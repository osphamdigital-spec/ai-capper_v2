# Claude Code — Setup Tracker
**Desktop PC (Windows 11 + WSL2) · Laptop (Windows 11 native) · iPhone 17 Pro Max**
Last updated: May 2026 · Claude Code 2.1 · 55+ skills active

---

## Status Key
| Symbol | Meaning |
|---|---|
| ✅ | Installed and working |
| ❌ | Not installed |
| ⏳ | Pending — install when back on that machine |
| N/A | Not applicable to this machine |

---

## Windows Foundations

| Item | Detail | Desktop | Laptop |
|---|---|---|---|
| PowerShell 7 + Windows Terminal | Default shell | ✅ | ✅ |
| Git 2.49+ | Version control | ✅ | ✅ |
| GitHub Desktop | Visual git client | ✅ | ✅ |
| VS Code 1.117+ | Code editor | ✅ | ✅ |
| Node.js 24 LTS | JavaScript runtime | ✅ | ✅ |
| Python 3.12 | Python runtime | ✅ | ✅ |
| uv | Python package manager | ✅ | ✅ |
| Tailscale | Private mesh network | ✅ | ✅ |
| GitHub CLI (gh) | GitHub from terminal | ✅ | ✅ |

---

## WSL2 + Ubuntu 24.04 (Desktop Only)

| Item | Detail | Desktop | Laptop |
|---|---|---|---|
| WSL2 + Ubuntu 24.04 | Linux environment inside Windows | ✅ | N/A |
| fnm + Node inside WSL | Node version manager in Ubuntu | ✅ | N/A |
| uv inside WSL | Python tools in Ubuntu | ✅ | N/A |
| SSH server enabled | For remote laptop access | ✅ | N/A |
| Windows Defender exclusions | WSL, npm, cache folders excluded | ✅ | N/A |
| Remote Desktop enabled | For iPhone RDP access | ✅ | N/A |

---

## Claude Code

| Item | Detail | Desktop | Laptop |
|---|---|---|---|
| Claude Code 2.1+ | Core AI coding agent | ✅ | ✅ |
| Authenticated to Anthropic | Logged in and working | ✅ | ✅ |
| Repomix 1.14+ | Codebase context tool | ✅ | ✅ |

---

## MCP Servers

| Item | Detail | Desktop | Laptop |
|---|---|---|---|
| filesystem | Read/write project files | ✅ | ✅ |
| github | GitHub integration | ✅ | ✅ |
| playwright | Browser automation | ✅ | ✅ |
| exa | Web search | ✅ | ✅ |
| e2b | Sandboxed code execution | ✅ | ✅ |
| elevenlabs | AI voiceover automation | ⏳ | ✅ |
| Google Drive | Drive integration via claude.ai | ✅ | ✅ |
| tokscript | TikTok/Instagram transcripts | ✅ | ✅ |
| sqlite | Fails on both machines — skip | ❌ | ❌ |

**Note:** MCP servers must be added once per new project folder. Run `claude mcp list` inside any new project folder and re-add if missing.

---

## Skills and Plugins

| Item | Detail | Desktop | Laptop |
|---|---|---|---|
| obra/superpowers | 14 skills — planning methodology | ✅ | ✅ |
| 10x-Content-Expert | 30 skills — loads from project folder only | ✅ | ✅ |
| create-viral-content | Viral social content skill | ✅ | ✅ |
| coreyhaines31/marketingskills | 10 skills — marketing pack | ✅ | ✅ |
| OpenClaudia write-blog | Blog writing skill | ✅ | ✅ |
| OpenClaudia social-content | Social content skill | ✅ | ✅ |
| OpenClaudia seo-audit | SEO audit skill | ✅ | ✅ |
| find-skills | Skill discovery helper | ✅ | ✅ |

---

## Media Tools

| Item | Detail | Desktop | Laptop |
|---|---|---|---|
| ffmpeg 8.1+ | Video/audio processing | ⏳ | ✅ |
| ImageMagick 7.1+ | Image processing and thumbnails | ⏳ | ✅ |
| yt-dlp | Video downloading | ⏳ | ✅ |
| Playwright Python library | For standalone Python scraper scripts | ❌ | ✅ |
| Playwright Chromium browser | Required for playwright scripts | ❌ | ✅ |

---

## Memory System and Config

| Item | Detail | Desktop | Laptop |
|---|---|---|---|
| claude-system repo | CLAUDE.md, LEARNINGS.md, TASKS.md | ✅ | ✅ |
| Pushed to GitHub (private) | Backup and cross-device sync | ✅ | ✅ |
| E2B API key set | In .bashrc / Windows env vars | ✅ | ✅ |
| ElevenLabs API key set | Free tier — set in environment | ⏳ | ✅ |
| GitHub personal access token | GITHUB_PERSONAL_ACCESS_TOKEN | ✅ | ⏳ |

---

## Remote Access

| Item | Detail | Desktop | Laptop | iPhone |
|---|---|---|---|---|
| Tailscale | Connected and signed in | ✅ | ✅ | ✅ |
| Remote Desktop enabled | Windows RDP on desktop | ✅ | N/A | N/A |
| Microsoft Remote Desktop app | iPhone RDP client | N/A | N/A | ❌ |
| Working Copy | Git client on phone | N/A | N/A | ❌ |

---

## Known Issues

| Issue | Detail | Status |
|---|---|---|
| SQLite MCP | Fails on both machines — empty db file issue | Ignore for now |
| MCP servers per project folder | Must re-add in each new project folder first time | Working as designed |
| GitHub token on laptop | Not yet set in Windows environment | ⏳ Pending |
| ffmpeg / ImageMagick / yt-dlp on desktop | Laptop done, desktop pending | ⏳ Pending |
| ElevenLabs on desktop | Laptop done, desktop pending | ⏳ Pending |

---

## Pending — When Back on Desktop

Run these in Ubuntu:

```bash
# Media tools
sudo apt install -y ffmpeg imagemagick python3-pip
pip install yt-dlp

# ElevenLabs MCP
claude mcp add elevenlabs -- uvx elevenlabs-mcp

# Playwright Python library
pip install playwright
python -m playwright install chromium
```

---

## Project Folder Notes

| Project | Location | Notes |
|---|---|---|
| claude-system | ~/projects/claude-system | Memory files — CLAUDE.md, LEARNINGS.md, TASKS.md |
| 10x-Content-Expert | ~/projects/10x-Content-Expert | Run claude from here for full 30 content skills |
| ai-capper | ~/projects/ai-capper | MLB odds scraper project — in progress |

---

## Monthly Maintenance

**Windows (both machines):**
```powershell
winget upgrade --all
```

**Ubuntu (desktop):**
```bash
sudo apt update && sudo apt upgrade -y
npm update -g
```
