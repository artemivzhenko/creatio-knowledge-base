"""Source-text helpers shared by the C# and JavaScript readers."""

from __future__ import annotations

_REGEX_AFTER = set("(,=:[!&|?{};")  # a "/" after one of these (or after `return`) starts a JavaScript regex literal, not a division


def _blank(s: str) -> str:
    return "".join("\n" if c == "\n" else " " for c in s)


def mask(text: str) -> str:
    """Comments and string, char, template and regex literal contents replaced by spaces (offsets and newlines kept),
    so braces and quotes in them do not count."""
    out, i, n = [], 0, len(text)
    prev = ""  # the last character of code seen, for telling a regex literal from a division
    while i < n:
        ch = text[i]
        two = text[i:i + 2]
        if two == "//":
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif two == "/*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(_blank(text[i:j]))
            i = j
        elif two in ('@"', '$"') or text[i:i + 3] in ('$@"', '@$"'):  # C# verbatim / interpolated strings
            start = i
            i = text.find('"', i) + 1
            while i < n:
                if text[i] == '"':
                    if text[i + 1:i + 2] == '"' and "@" in text[start:start + 3]:
                        i += 2
                        continue
                    break
                i += 1
            i += 1
            out.append('"' + _blank(text[start + 1:i - 1]) + '"')
            prev = '"'
        elif ch in "\"'`":
            j = i + 1
            while j < n and text[j] != ch and (ch == "`" or text[j] != "\n"):
                j += 2 if text[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(ch + _blank(text[i + 1:j - 1]) + ch if j - i >= 2 else text[i:j])
            prev = ch
            i = j
        elif ch == "/" and (prev in _REGEX_AFTER or text[max(0, i - 16):i].rstrip().endswith("return")):
            j, in_class = i + 1, False
            while j < n and text[j] != "\n" and (in_class or text[j] != "/"):
                in_class = (in_class or text[j] == "[") and text[j] != "]"
                j += 2 if text[j] == "\\" else 1
            if j >= n or text[j] == "\n":  # not a regex after all
                out.append(ch)
                prev = ch
                i += 1
                continue
            out.append("/" + " " * (j - i - 1) + "/")
            prev = "/"
            i = j + 1
        else:
            out.append(ch)
            if not ch.isspace():
                prev = ch
            i += 1
    return "".join(out)
