# OpenAI Responses：在 opencode 中的协议映射与实现（可复刻）

> 目标：解释 opencode 如何把内部的“对话/工具/多模态”抽象映射到 OpenAI **Responses API**（含流式 SSE），以及如何把返回结果还原成统一的内容/工具调用流，方便你在另一个 SDK 中按同样机制复刻。

---

## 1) 总览：opencode 的 “Responses 适配层” 在做什么

opencode 并不直接把业务逻辑写死到 OpenAI 的 JSON 结构里，而是：

1. 在内部使用统一的 **prompt 表示**（角色 + 分段 content：text/file/tool-call/tool-result/reasoning 等）。
2. 在 provider 层实现一个 **Responses 适配器**，负责：
   - 把内部 prompt → `POST /v1/responses` 的 `input` 数组；
   - 把内部 tools / toolChoice → Responses 的 `tools` / `tool_choice`；
   - 把 providerOptions（如 `reasoningEffort` / `textVerbosity` / `store` / `include` 等）映射到请求体；
   - 非流式：解析 `output[]` 为统一 content；
   - 流式：解析 SSE 事件流为统一 stream parts（text/tool/reasoning/source/finish 等）。

实现入口主要在：

- `packages/opencode/src/provider/sdk/openai-compatible/src/responses/openai-responses-language-model.ts`
- `packages/opencode/src/provider/sdk/openai-compatible/src/responses/convert-to-openai-responses-input.ts`
- `packages/opencode/src/provider/sdk/openai-compatible/src/responses/openai-responses-prepare-tools.ts`
- `packages/opencode/src/provider/sdk/openai-compatible/src/responses/openai-responses-api-types.ts`

---

## 2) 请求：内部调用参数如何变成 `/responses` 的 JSON Body

### 2.1 Body 的骨架（opencode 实际发送）

构造请求体的核心在 `OpenAIResponsesLanguageModel.getArgs()`。

它最终构造出类似如下的结构（省略部分可选字段）：

```ts
const baseArgs = {
  model: this.modelId,
  input,                       // 关键：由 prompt 转换得到
  temperature,
  top_p: topP,
  max_output_tokens: maxOutputTokens,

  // text.format / text.verbosity（JSON 模式 & verbosity）
  text: { format: ..., verbosity: ... },

  // tools / tool_choice（由 prepareResponsesTools 转换）
  tools: openaiTools,
  tool_choice: openaiToolChoice,

  // provider options（OpenAI Responses 支持的字段）
  store,
  include,
  instructions,
  previous_response_id,
  parallel_tool_calls,
  max_tool_calls,
  metadata,
  user,
  service_tier,
  prompt_cache_key,
  safety_identifier,
  top_logprobs,

  // reasoning 模型专属
  reasoning: { effort: ..., summary: ... },

  // 某些模型要求
  truncation: "auto",
}
```

对应代码（节选）在 `.../openai-responses-language-model.ts`：

```ts
const baseArgs = {
  model: this.modelId,
  input,
  temperature,
  top_p: topP,
  max_output_tokens: maxOutputTokens,
  ...((responseFormat?.type === "json" || openaiOptions?.textVerbosity) && {
    text: {
      ...(responseFormat?.type === "json" && { format: ... }),
      ...(openaiOptions?.textVerbosity && { verbosity: openaiOptions.textVerbosity }),
    },
  }),
  // provider options...
  service_tier: openaiOptions?.serviceTier,
  include,
  top_logprobs: topLogprobs,
  ...(modelConfig.isReasoningModel && { reasoning: { effort: ..., summary: ... } }),
  ...(modelConfig.requiredAutoTruncation && { truncation: "auto" }),
}
```

### 2.2 “reasoning 模型限制” 的处理

opencode 会基于 `modelId` 推断一个 `modelConfig`（是否 reasoning、system message 模式、是否需要 truncation、是否支持 flex/priority 等），并做保护性处理：

- reasoning 模型：移除 `temperature` / `top_p`（并产生 warnings）。
- 非 reasoning 模型：如果你传了 `reasoningEffort` / `reasoningSummary`，会产生 warnings。
- `service_tier=flex/priority`：不支持的模型会被移除并产生 warnings。

相关代码在 `.../openai-responses-language-model.ts` 的 `getResponsesModelConfig()` 和 `getArgs()`。

---

## 3) `input[]`：内部 Prompt 如何转换成 Responses 的输入项

转换发生在 `convertToOpenAIResponsesInput()`（`.../convert-to-openai-responses-input.ts`）。

### 3.1 system / developer

内部 prompt 中的 `role: "system"` 会按 `systemMessageMode` 转换为：

- `"system"`：输入为 `{ role: "system", content: "..." }`
- `"developer"`：输入为 `{ role: "developer", content: "..." }`
- `"remove"`：丢弃并发出 warning

节选：

```ts
case "system": {
  switch (systemMessageMode) {
    case "system": input.push({ role: "system", content }); break
    case "developer": input.push({ role: "developer", content }); break
    case "remove": warnings.push({ type: "other", message: "system messages are removed for this model" }); break
  }
}
```

### 3.2 user：文本、图片、PDF（含 URL / file_id / data URL）

user 消息会被拆成 `input_text` / `input_image` / `input_file`：

- 图片：
  - URL → `image_url`
  - 若字符串且匹配 `fileIdPrefixes`（如 `file-` / `assistant-`）→ `file_id`
  - 否则把二进制转换为 `data:<mime>;base64,<...>`
  - 支持 `detail`（来自 `part.providerOptions?.openai?.imageDetail`）
- PDF：
  - URL → `file_url`
  - 字符串且匹配 `fileIdPrefixes` → `file_id`
  - 否则 `{ filename, file_data: data:application/pdf;base64,... }`

节选：

```ts
return { type: "input_text", text: part.text }

return {
  type: "input_image",
  ...(part.data instanceof URL
    ? { image_url: part.data.toString() }
    : typeof part.data === "string" && isFileId(part.data, fileIdPrefixes)
      ? { file_id: part.data }
      : { image_url: `data:${mediaType};base64,${convertToBase64(part.data)}` }),
  detail: part.providerOptions?.openai?.imageDetail,
}
```

### 3.3 assistant：输出文本、工具调用、provider 执行的工具结果、reasoning

assistant 内容里最关键的是 4 种分支：

#### A) 输出文本

```ts
input.push({
  role: "assistant",
  content: [{ type: "output_text", text: part.text }],
  id: (part.providerOptions?.openai?.itemId as string) ?? undefined,
})
```

`id` 会被带回去用于 item 引用/关联（尤其对 reasoning / tool 的 “item_reference” 很重要）。

#### B) 工具调用（client-side function tools）

如果是普通工具调用（且不是 provider 执行的 built-in tool），会转成 Responses 的 `function_call`：

```ts
input.push({
  type: "function_call",
  call_id: part.toolCallId,
  name: part.toolName,
  arguments: JSON.stringify(part.input),
  id: (part.providerOptions?.openai?.itemId as string) ?? undefined,
})
```

#### C) provider 执行的 built-in tools：只保留引用（item_reference）

assistant 的 `tool-result` 在这里**被视为 provider 执行的工具结果**。

当 `store=true` 时，opencode 不把 tool-result 的全文塞回输入，而是用 `item_reference` 引用该 tool call 的 id：

```ts
if (store) input.push({ type: "item_reference", id: part.toolCallId })
else warnings.push({ type: "other", message: `Results for OpenAI tool ... are not sent ... when store is false` })
```

这点是复刻时最容易踩坑的地方：你的 SDK 必须理解 `store` 对“历史回传/可引用”的影响。

#### D) reasoning：store=true 用引用；store=false 直接发 reasoning 对象

reasoning part 会读取 `providerOptions` 来拿 `itemId`（也就是 OpenAI 返回的 reasoning item id）。

- `store=true`：仅发 `{ type: "item_reference", id: reasoningId }`，避免重复传 reasoning 内容。
- `store=false`：把 reasoning 的 summary 文本拼成 `{ type:"reasoning", id, encrypted_content?, summary:[...] }` 直接传回。

---

## 4) tools / tool_choice：如何映射到 Responses

映射在 `prepareResponsesTools()`（`.../openai-responses-prepare-tools.ts`）：

1. 普通 function tool → `{ type:"function", name, description, parameters, strict }`
2. provider-defined（OpenAI built-in）按 `tool.id` 分发成：
   - `file_search` / `web_search` / `web_search_preview` / `code_interpreter` / `image_generation` / `local_shell`
3. `toolChoice`：
   - `"auto" | "none" | "required"` 原样透传
   - 指定某个 toolName：若是 built-in（例如 `file_search`）→ `{ type: "file_search" }`；否则 → `{ type:"function", name }`

节选：

```ts
case "tool":
  return {
    toolChoice:
      toolChoice.toolName === "code_interpreter" || toolChoice.toolName === "file_search" || ...
        ? { type: toolChoice.toolName }
        : { type: "function", name: toolChoice.toolName },
  }
```

---

## 5) 非流式响应：`output[]` 如何还原成统一 content

非流式调用在 `OpenAIResponsesLanguageModel.doGenerate()`：

- 请求：`POST /responses`，zod 校验返回 JSON 的结构；
- 若 `response.error` 非空：抛 `APICallError`；
- 遍历 `response.output[]`，把每个 output item 映射为统一 `content[]`：
  - `message` → `text`（并提取 `annotations` 生成 `source`）
  - `function_call` → `tool-call`（这是 client-side tool call）
  - `web_search_call` / `file_search_call` / `code_interpreter_call` / `image_generation_call` / `computer_call` → 生成一对 `tool-call` + `tool-result` 且 `providerExecuted: true`
  - `reasoning` → `reasoning`（用 `summary_text` 组成 reasoning 内容；并把 `encrypted_content` 放入 providerMetadata）

finishReason 与 usage：

- finishReason 通过 `mapOpenAIResponseFinishReason()` 处理：如果发生 client-side function_call，则 finishReason 倾向于 `"tool-calls"`。
- usage 会带 `reasoningTokens` / `cachedInputTokens`（来自 Responses `usage.*_details`）。

---

## 6) 流式响应（SSE）：事件协议与 opencode 的状态机

### 6.1 opencode 识别的事件类型（zod union）

在 `.../openai-responses-language-model.ts` 里，`openaiResponsesChunkSchema` 明确列出会处理的 chunk：

- `response.created`
- `response.output_item.added`
- `response.output_item.done`
- `response.output_text.delta`
- `response.function_call_arguments.delta`
- `response.image_generation_call.partial_image`
- `response.code_interpreter_call_code.delta`
- `response.code_interpreter_call_code.done`
- `response.output_text.annotation.added`
- `response.reasoning_summary_part.added`
- `response.reasoning_summary_text.delta`
- `response.completed` / `response.incomplete`
- `error`
- 以及一个兜底 `{ type: string }`（未知事件不会直接崩）

节选：

```ts
const openaiResponsesChunkSchema = z.union([
  textDeltaChunkSchema,
  responseFinishedChunkSchema,
  responseCreatedChunkSchema,
  responseOutputItemAddedSchema,
  responseOutputItemDoneSchema,
  responseFunctionCallArgumentsDeltaSchema,
  responseImageGenerationCallPartialImageSchema,
  responseCodeInterpreterCallCodeDeltaSchema,
  responseCodeInterpreterCallCodeDoneSchema,
  responseAnnotationAddedSchema,
  responseReasoningSummaryPartAddedSchema,
  responseReasoningSummaryTextDeltaSchema,
  errorChunkSchema,
  z.object({ type: z.string() }).loose(),
])
```

### 6.2 流式“统一输出”的关键状态

为了把 Responses 的 SSE 事件拼成稳定的“文本流 + 工具输入流 + reasoning 流”，opencode 在 `doStream()` 中维护了：

- `currentTextId: string | null`
  - 用于给 `text-start/text-delta/text-end` 绑定一个稳定 id
  - 备注：代码注释明确提到某些上游（如 Copilot）可能在 text delta 中旋转 `item_id`，因此需要稳定化
- `ongoingToolCalls: Record<number, { toolName, toolCallId, codeInterpreter? } | undefined>`
  - 用 `output_index` 追踪正在流式输出的 tool call 输入（尤其是 function_call arguments delta）
- `activeReasoning: Record<number, { canonicalId, encryptedContent?, summaryParts }>`
  - 用 `output_index` 追踪 reasoning，因为有的上游会在每个事件里变动 item id
- `currentReasoningOutputIndex: number | null`
  - 用于把 `response.reasoning_summary_*` 事件归因到当前活跃 reasoning

### 6.3 核心拼装规则（按事件）

#### A) `response.output_item.added`

- `message`：发 `text-start`（并记录 `currentTextId = item.id`）
- `function_call`：登记 `ongoingToolCalls[output_index]` 并发 `tool-input-start`
- `web_search_call` / `computer_call`：同样发 `tool-input-start`（随后 done 时会补齐 tool-call + tool-result）
- `code_interpreter_call`：发 `tool-input-start`，然后立刻发一个 `tool-input-delta` 作为 JSON 前缀：

```ts
controller.enqueue({
  type: "tool-input-delta",
  id: value.item.id,
  delta: `{"containerId":"${value.item.container_id}","code":"`,
})
```

- `reasoning`：发 `reasoning-start`（id 形如 `${item.id}:0`），并记录 `activeReasoning` / `currentReasoningOutputIndex`

#### B) 文本增量：`response.output_text.delta`

- 若没有 `currentTextId`，会先发一个 `text-start`（并把 `currentTextId` 固定下来）
- 每个 delta 产生 `text-delta`
- 若开启 logprobs，会收集 `logprobs`

#### C) 函数工具输入增量：`response.function_call_arguments.delta`

用 `output_index` 找到正在进行的 tool call，然后发 `tool-input-delta`：

```ts
controller.enqueue({ type: "tool-input-delta", id: toolCall.toolCallId, delta: value.delta })
```

#### D) code_interpreter 的 code 增量：`response.code_interpreter_call_code.delta/done`

这里有一个很关键的细节：delta 是“嵌进 JSON string 里的代码”，所以需要转义：

```ts
delta: JSON.stringify(value.delta).slice(1, -1)
```

当 `...code.done` 到来时：

1. 追加 `'"}`` 关闭 JSON 字符串；
2. 发 `tool-input-end`；
3. 立刻发 `tool-call`（providerExecuted=true），其 input 是完整 JSON：

```ts
controller.enqueue({
  type: "tool-call",
  toolCallId: toolCall.toolCallId,
  toolName: "code_interpreter",
  input: JSON.stringify({ code: value.code, containerId: toolCall.codeInterpreter!.containerId }),
  providerExecuted: true,
})
```

#### E) `response.output_item.done`

- `function_call`：
  - `tool-input-end`
  - 然后发统一 `tool-call`（这是 client-side tool call，`hasFunctionCall=true`）
- `web_search_call` / `computer_call`：
  - `tool-input-end`
  - 发 `tool-call`（providerExecuted=true）
  - 再立刻发 `tool-result`（providerExecuted=true）
- `file_search_call` / `image_generation_call` / `code_interpreter_call`：
  - 发 `tool-result`（providerExecuted=true）
- `message`：
  - 如果存在 `currentTextId`，会 `text-end` 并清空
- `reasoning`：
  - 对 `activeReasoning[output_index].summaryParts` 中的每个 part 发 `reasoning-end`
  - 清理 `activeReasoning` 并更新 `currentReasoningOutputIndex`

#### F) reasoning summary：`response.reasoning_summary_part.added` + `response.reasoning_summary_text.delta`

opencode 把 reasoning 允许拆成多个 summary part（index 0 是第一次 start 时创建的；>0 的 part 会额外发 `reasoning-start`）：

```ts
if (activeItem && value.summary_index > 0) {
  activeItem.summaryParts.push(value.summary_index)
  controller.enqueue({ type: "reasoning-start", id: `${activeItem.canonicalId}:${value.summary_index}`, ... })
}
```

每个 `...summary_text.delta` → `reasoning-delta`（id 用 `${canonicalId}:${summary_index}`）。

#### G) 注释（citation）：`response.output_text.annotation.added`

映射为统一 `source` part（url 或 document）。

#### H) 结束：`response.completed` / `response.incomplete`

更新：

- `finishReason`（同非流式一样经过 `mapOpenAIResponseFinishReason`）
- `usage`（含 reasoningTokens/cachedInputTokens）
- `serviceTier`（可写入 providerMetadata）

最后在 `flush()`：

- 关闭可能遗留的 `text-end`
- emit `{ type: "finish", finishReason, usage, providerMetadata }`

---

## 7) ProviderOptions：Responses 特有字段在 opencode 里的 schema

`openaiResponsesProviderOptionsSchema`（位于 `.../openai-responses-language-model.ts` 文件末尾附近）定义了该适配器支持的 options：

- `store` / `include` / `instructions` / `previousResponseId`
- `parallelToolCalls` / `maxToolCalls`
- `logprobs`（boolean 或 top-N 数字；会映射到 `top_logprobs`）
- `serviceTier: "auto" | "flex" | "priority"`
- `textVerbosity: "low" | "medium" | "high"`（映射到 `text.verbosity`）
- `reasoningEffort` / `reasoningSummary`（映射到 `reasoning.effort` / `reasoning.summary`）
- `promptCacheKey` / `safetyIdentifier` / `metadata` / `user`

复刻时建议直接把这些当作“provider 专属扩展字段”，并在最终 HTTP body merge 时保证它们优先级清晰。

---

## 8) 复刻时最常见的坑（opencode 的实现给出的答案）

1. **`store` 与 `item_reference` 的关系**
   - `store=true`：历史可被引用，所以 tool-result/reasoning 多用 `item_reference` 回传。
   - `store=false`：opencode 会警告“tool 结果不会被回传”，reasoning 则走“直接发送 reasoning summary”分支。
2. **SSE 事件里的 id 不稳定**
   - opencode 为 text 用 `currentTextId` 稳定化；
   - 为 reasoning 用 `output_index` 作为主键跟踪。
3. **code_interpreter 的 code delta 必须转义**
   - 否则你拼出来的 JSON input 不是合法字符串，后续 tool-call 无法解析。
4. **built-in tools 的 `providerExecuted` 语义**
   - Responses 返回的 web_search/file_search/code_interpreter/image_generation/computer_call 是“模型侧执行”的，opencode 直接发 tool-call + tool-result（`providerExecuted:true`）；
   - `function_call` 则是“客户端需要执行”的工具调用，会导致 finishReason 更偏向 `"tool-calls"`。
5. **自动 include**
   - logprobs/web_search/code_interpreter 会触发自动 `include`（例如 `"message.output_text.logprobs"`、`"web_search_call.action.sources"`、`"code_interpreter_call.outputs"`），否则返回里可能缺字段。

---

## 9) 复刻实现的最小清单（建议）

1. 定义你 SDK 内部的统一 prompt/content/stream 抽象。
2. 实现 `prompt -> input[]`：
   - system/developer 模式可配置；
   - user 多模态（URL/file_id/data URL）；
   - assistant 的 function_call / tool-result 引用策略（store=true 时优先 item_reference）。
3. 实现 `tools/tool_choice -> Responses tools/tool_choice`。
4. 非流式：解析 `output[]`，统一成 text/reasoning/tool-call/tool-result/source，并输出 usage/finishReason/providerMetadata。
5. 流式：按 SSE 事件实现状态机（text/tool/reasoning/source），保证 id 稳定、支持 code_interpreter 的 JSON 拼装、在 flush 时正确收尾并输出 finish。

