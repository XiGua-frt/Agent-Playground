# RAG Markdown 切分策略总结

## 一、模块概览

该模块实现了一套针对 Markdown 文档的两阶段切分流水线，目标是在保留语义完整性的前提下，将文档切成适合向量检索（RAG）的 chunk，每个 chunk 携带原文位置和标题路径元数据。

```
原始 Markdown 文本
        ↓
_split_paragraphs_with_headings()   # 第一阶段：语义感知分段
        ↓
paragraphs 列表（最小语义单元）
        ↓
_chunk_paragraphs()                 # 第二阶段：Token 感知打包 + 滑动重叠
        ↓
chunks 列表（最终检索单元）
```

---

## 二、第一阶段：`_split_paragraphs_with_headings`

### 核心思路

逐行扫描文本，以 Markdown 标题行和空行作为段落边界，同时用一个栈维护当前所在的标题层级路径。

### 关键变量

| 变量 | 类型 | 作用 |
|------|------|------|
| `heading_stack` | `List[str]` | 记录当前标题路径，如 `["第一章", "1.1 背景"]` |
| `buf` | `List[str]` | 暂存当前段落的内容行，遇到边界时统一 flush |
| `char_pos` | `int` | 字符位置游标，每行结束后 `+= len(行) + 1` |
| `paragraphs` | `List[Dict]` | 输出结果，每项含 content / heading_path / start / end |

### 处理逻辑

**遇到标题行（`raw.strip().startswith("#")`）**

1. 先调用 `flush_buf()` 把 `buf` 里的内容输出为一个 paragraph
2. 计算标题级别：`level = len(raw) - len(raw.lstrip('#'))`
3. 截断 `heading_stack` 到 `level - 1` 层，再 push 当前标题
4. `buf = []` 清空缓冲，`continue` 跳过，标题行本身不进入内容

**遇到空行**

1. 调用 `flush_buf()` 输出当前 `buf`
2. `buf = []` 清空，空行是段落的天然分隔符

**遇到普通内容行**

- `buf.append(raw)`，继续积累

**循环结束后**

- 再调用一次 `flush_buf()`，处理文件末尾没有空行的情况
- 若 `paragraphs` 为空（无结构文本），把整个原文作为单个 paragraph 兜底

### `flush_buf` 的输出结构

```python
{
    "content": "段落文本内容",
    "heading_path": "第一章 > 1.1 背景",   # heading_stack 用 ' > ' 拼接，无标题则为 None
    "start": 123,                           # 估算的起始字符偏移
    "end": 456,                             # 当前 char_pos
}
```

### `heading_stack` 维护示意

```
遇到 # 第一章      → 栈：["第一章"]
遇到 ## 1.1 背景   → 栈：["第一章", "1.1 背景"]
遇到 ## 1.2 方法   → 截断到第0层再追加 → 栈：["第一章", "1.2 方法"]
遇到 # 第二章      → 截断到第0层再追加 → 栈：["第二章"]
```

---

## 三、第二阶段：`_chunk_paragraphs`

### 核心思路

以第一阶段的 paragraph 列表为输入，按 token 数量上限贪心打包，在相邻 chunk 之间保留重叠窗口，形成软性语义衔接。

### 关键变量

| 变量 | 类型 | 作用 |
|------|------|------|
| `cur` | `List[Dict]` | 当前正在积累的 paragraph 缓冲 |
| `cur_tokens` | `int` | `cur` 里所有内容的 token 计数 |
| `i` | `int` | 遍历游标，某些情况下不递增 |
| `chunks` | `List[Dict]` | 输出结果 |

### 处理逻辑

**能放入（`cur_tokens + p_tokens <= chunk_tokens` 或 `cur` 为空）**

- `cur.append(p)`，`cur_tokens += p_tokens`，`i += 1`
- `cur` 为空时强制放入，防止单个超长 paragraph 导致死循环

**放不下（else 分支）**

1. 把 `cur` 封装为一个 chunk 输出（`i` **不递增**，当前 paragraph 等待下一轮）
2. 构建重叠窗口：从 `cur` 末尾反向遍历，贪心累计不超过 `overlap_tokens` 的 paragraph，作为新的 `cur` 起点
3. 若 `overlap_tokens == 0`，直接清空 `cur`

**循环结束后**

- `cur` 里的剩余内容统一输出为最后一个 chunk

### chunk 的输出结构

```python
{
    "content": "段落A\n\n段落B\n\n段落C",   # 多个 paragraph 用双换行拼接
    "start": cur[0]["start"],               # 第一个 paragraph 的起始位置
    "end": cur[-1]["end"],                  # 最后一个 paragraph 的结束位置
    "heading_path": "第一章 > 1.2 方法",    # 从 cur 尾部往前找最近的 heading_path
}
```

### 滑动窗口示意（chunk_tokens=100，overlap_tokens=20）

```
paragraphs:  [P1(30)] [P2(40)] [P3(35)] [P4(50)] [P5(20)]

第1个chunk：P1+P2+P3 = 105 → 放不下P3时输出P1+P2，重叠取P2(40>20取P2尾部)
第2个chunk：从P2尾部重叠开始，继续打包P3+P4 ...
```

---

## 四、两阶段对比

| 维度 | 第一阶段 | 第二阶段 |
|------|---------|---------|
| 切分依据 | 语义边界（标题、空行） | Token 数量上限 |
| 最小单元 | 单个自然段落 | 不再拆分，只做合并 |
| 元数据 | heading_path / start / end | 继承并汇总自 paragraphs |
| 边界处理 | 硬切（以结构为准） | 软化（重叠窗口） |
| 输出 | paragraphs 列表 | chunks 列表 |

---

## 五、面试高频问题及参考回答

### 基础理解类

**Q1：为什么要分两个阶段，直接按 token 数切不行吗？**

直接按 token 数切会无视 Markdown 的语义结构，可能把同一段落、同一标题下的内容硬截断，导致 chunk 语义不完整，检索时召回的片段缺乏上下文。两阶段的好处是先用结构边界保证最小单元的语义完整，再用 token 预算控制 chunk 大小，两个目标互不干扰。

**Q2：`heading_stack` 是怎么维护的，为什么要截断？**

`heading_stack` 记录当前所在的完整标题路径。遇到同级或更高级的标题时，必须先把栈里更深层的旧路径弹出，否则路径会错误地把新标题挂在旧的子标题下面。截断到 `level - 1` 再 push，保证栈里永远只有从根到当前位置的唯一路径。

**Q3：`while` 循环里为什么有时候 `i` 不递增？**

当前 paragraph 放不下时，需要先把 `cur` 输出并重建重叠窗口，然后让同一个 paragraph 在新的 `cur` 基础上重新参与下一轮判断。如果此时递增 `i`，这个 paragraph 就会被跳过，造成内容丢失。

**Q4：`not cur` 这个条件的作用是什么？**

如果某个 paragraph 自身的 token 数就超过了 `chunk_tokens`，而 `cur` 恰好为空，按正常逻辑它永远放不进去，`i` 永远不递增，程序死循环。`not cur` 作为强制兜底，保证 `cur` 为空时无论大小都必须接收，确保循环能推进。

**Q5：`heading_path` 为什么从 `cur` 尾部往前找，而不是从头？**

`cur` 里靠后的 paragraph 在文档中位置更靠后，所属的标题路径更能代表这批内容当前所在的位置。从尾部找到的第一个有效 `heading_path` 是最接近 chunk 结尾内容的标题，语义上更准确。

---

### 设计与权衡类

**Q6：重叠窗口的作用是什么，overlap_tokens 如何取值？**

重叠保证跨 chunk 边界的语义不被硬截断，让相邻两个 chunk 共享一段内容，检索时即使查询落在边界附近也能召回完整上下文。overlap_tokens 通常取 chunk_tokens 的 10%～20%，过大会造成大量冗余，过小则失去软化效果。

**Q7：`start` 和 `end` 的计算准确吗，有什么局限？**

`flush_buf` 里用 `max(0, end_pos - len(content))` 估算 `start`，这是近似值，因为 `content` 经过了 `strip()`，去掉了首尾空白，实际字符数与原文偏移可能有出入。对于需要精确字符定位的场景（比如高亮原文），这里的偏移可能需要更精确的追踪方式。

**Q8：如果 Markdown 标题层级不规范（如直接从 `#` 跳到 `###`）怎么处理？**

代码会按实际遇到的 level 截断 `heading_stack`。从 `#` 跳到 `###` 时，`level=3`，`len(heading_stack)=1`，不满足截断条件，直接追加，栈变为 `["第一章", "小节"]`，中间跳过的 `##` 层级不会产生影响，路径只反映实际出现过的标题。

**Q9：这套方案和纯递归字符分割（RecursiveCharacterTextSplitter）相比有什么优劣？**

| | 本方案 | 递归字符分割 |
|---|---|---|
| 优点 | 保留标题结构语义，chunk 有归属路径 | 实现简单，通用性强 |
| 缺点 | 依赖 Markdown 格式规范，对无结构文本退化为整段 | 不感知语义边界，可能割裂句子 |

本方案更适合结构良好的技术文档、知识库；递归分割更适合非结构化的纯文本。

**Q10：`_approx_token_len` 只是近似值，误差会带来什么问题？**

如果估算值偏小，实际 chunk 的 token 数可能超出模型上下文窗口，导致截断或报错。如果估算值偏大，chunk 会被过早切分，导致 chunk 数量增多、召回时碎片化。生产中通常用 `tiktoken` 等精确分词器替代近似估算，或在近似值基础上保留一定安全余量。

---

### 边界与异常类

**Q11：如果整个文档没有任何 Markdown 标题怎么处理？**

`heading_stack` 始终为空，所有 paragraph 的 `heading_path` 都为 `None`。第一阶段仍能正常按空行分段，第二阶段按 token 打包，只是 chunk 没有标题元数据。若连空行都没有，整个文本会作为一个 paragraph 进入第二阶段。

**Q12：文档末尾没有换行符，最后一段内容会丢失吗？**

不会。第一阶段循环结束后有一次兜底的 `flush_buf(char_pos)`，第二阶段循环结束后也有对 `cur` 剩余内容的兜底输出，两处都做了保护。

**Q13：如果某个段落内容为纯空白（strip 后为空），会被输出吗？**

不会。`flush_buf` 里在 `strip()` 之后检查 `if not content: return`，纯空白内容直接跳过，不会产生空的 paragraph。