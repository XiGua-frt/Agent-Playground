

def _split_paragraphs_with_headings(text: str) -> List[Dict]:
    """根据标题层次分割段落，保持语义完整性"""
    lines = text.splitlines()
    heading_stack: List[str] = []
    paragraphs: List[Dict] = []
    buf: List[str] = []
    char_pos = 0

    def flush_buf(end_pos: int):
        if not buf:
            return
        content = "\n".join(buf).strip()
        if not content:
            return
        paragraphs.append({
            "content": content,
            "heading_path": " > ".join(heading_stack) if heading_stack else None,
            "start": max(0, end_pos - len(content)),
            "end": end_pos,
        })

    for ln in lines:
        raw = ln
        # 检测是否为 Markdown 标题行 (如 # 标题1, ## 标题2)
        if raw.strip().startswith("#"):
            flush_buf(char_pos)  # 先保存之前的段落内容
            
            # 计算标题层级 (有几个 # 就是几级)
            level = len(raw) - len(raw.lstrip('#'))
            title = raw.lstrip('#').strip()
            
            if level <= 0:
                level = 1
            
            # 维护标题栈：如果当前标题层级比栈深浅，则弹出旧的路径
            if level <= len(heading_stack):
                heading_stack = heading_stack[:level-1]
            
            heading_stack.append(title)
            char_pos += len(raw) + 1
            buf = [] # 清空缓存准备处理新内容
            continue

        # 处理普通段落内容
        if raw.strip() == "":
            flush_buf(char_pos)
            buf = []
        else:
            buf.append(raw)
        
        char_pos += len(raw) + 1

    flush_buf(char_pos) # 处理最后剩余的内容
    
    if not paragraphs:
        paragraphs = [{"content": text, "heading_path": None, "start": 0, "end": len(text)}]
    
    return paragraphs


from typing import List, Dict

def _chunk_paragraphs(
    paragraphs: List[Dict], 
    chunk_tokens: int, 
    overlap_tokens: int
) -> List[Dict]:
    """
    基于 Token 数量的智能分块逻辑。
    
    Args:
        paragraphs: 包含段落内容的列表，每个元素为 Dict。
        chunk_tokens: 每个分块允许的最大 Token 数量。
        overlap_tokens: 分块之间重叠部分的 Token 数量。
    """
    chunks: List[Dict] = []
    cur: List[Dict] = []
    cur_tokens = 0
    i = 0

    while i < len(paragraphs):
        p = paragraphs[i]
        # 估算当前段落的 token 长度，最小为 1
        p_tokens = _approx_token_len(p["content"]) or 1

        # 如果当前分块还没满，或者 cur 为空（防止单个段落超长导致的死循环）
        if cur_tokens + p_tokens <= chunk_tokens or not cur:
            cur.append(p)
            cur_tokens += p_tokens
            i += 1
        else:
            # 1. 封装当前分块
            content = "\n\n".join(x["content"] for x in cur)
            start = cur[0]["start"]
            end = cur[-1]["end"]
            # 寻找该块中最近的一个标题路径
            heading_path = next(
                (x["heading_path"] for x in reversed(cur) if x.get("heading_path")), 
                None
            )
            
            chunks.append({
                "content": content,
                "start": start,
                "end": end,
                "heading_path": heading_path,
            })

            # 2. 构建重叠部分（为下一个分块做准备）
            if overlap_tokens > 0 and cur:
                kept: List[Dict] = []
                kept_tokens = 0
                # 从当前块末尾反向寻找符合重叠长度的段落
                for x in reversed(cur):
                    t = _approx_token_len(x["content"]) or 1
                    if kept_tokens + t > overlap_tokens and kept: # 确保至少保留一个段落
                        break
                    kept.append(x)
                    kept_tokens += t
                
                cur = list(reversed(kept))
                cur_tokens = kept_tokens
            else:
                cur = []
                cur_tokens = 0

    # 3. 处理最后一个分块
    if cur:
        content = "\n\n".join(x["content"] for x in cur)
        heading_path = next(
            (x["heading_path"] for x in reversed(cur) if x.get("heading_path")), 
            None
        )
        chunks.append({
            "content": content,
            "start": cur[0]["start"],
            "end": cur[-1]["end"],
            "heading_path": heading_path,
        })

    return chunks