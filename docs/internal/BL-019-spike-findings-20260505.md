# BL-019 Spike: Remotion Agent Skill

**Date:** 2026-05-05  
**Source:** https://www.remotion.dev / https://github.com/remotion-dev/skills  
**Status:** DONE

---

## What Remotion Is

Remotion is a React-based framework for producing real video files — MP4 (H.264/H.265), WebM, ProRes, GIF. It is not a browser-preview tool. Output is file-based media that plays anywhere. The rendering pipeline is: React component tree → Puppeteer (headless Chrome) renders each frame as PNG → FFmpeg encodes the frame sequence into the target format. This is CPU-intensive and frame-accurate.

FFmpeg is bundled as an npm dependency since v4.0 (released 2024). On macOS and Windows it auto-downloads on first render — no manual install needed. The local install story is genuinely low-friction: `npx create-video@latest`, answer a few prompts, `npm run dev`, start prompting Claude. Two commands to a working project.

Remotion is very actively maintained: 45,800 GitHub stars, v4.0.457 released May 4, 2026. Not a risk from a sustainability perspective.

---

## The Remotion Agent Skill Already Exists, First-Party

This is the key finding. **Remotion ships an official Claude Code skill** at [remotion-dev/skills](https://github.com/remotion-dev/skills) (~3,000 stars, actively maintained by the Remotion team). It is not a community wrapper — it is the Remotion team's own first-party skill for Claude Code integration.

Installation: `npx skills add remotion-dev/skills`, or opt in during `npx create-video@latest`. The skill places a `.claude/` folder in your project with Remotion-specific conventions, animation patterns, sequence management rules, and integrations for Three.js, Lottie, and TailwindCSS. Remotion's own documentation includes a "Prompting videos with Claude Code" page at `remotion.dev/docs/ai/claude-code`.

The workflow is tested and documented: scaffold a project, start the preview server, open Claude Code in the project directory, describe what you want. Community feedback confirms it works reliably for the target use case — promotional videos with text reveals, terminal typing effects, branding overlays, and slide transitions. Complexity ceiling: anything with many simultaneously moving elements, precise spatial positioning, or multi-track audio degrades quickly (timing drift, positioning errors accumulate).

---

## Answers to Spike Questions

**1. What does Remotion produce?**  
Real video files: MP4 (H.264/H.265), WebM (VP8/VP9/AV1), ProRes, GIF. Not animated SVG. Not browser-only. FFmpeg-encoded from Puppeteer-rendered frames.

**2. What is the skill's interface?**  
User describes the video in natural language in Claude Code. Claude writes the React/Remotion component code. The skill's `.claude/` content guides Claude on Remotion conventions. Not templated — generative from description. Preview is live in the browser; rendering to file is on-demand.

**3. Could this replace the "demo terminal recording" item in MS-001?**  
Yes. Terminal animation is a documented strength of Remotion + Claude Code (typing effects, command output reveals, syntax highlighting). Multiple community demos confirm this. The branded promotional video use case (intro → terminal demo → outro) is exactly the pattern tutorials show. BL-032 (Remotion demo video) should proceed using this approach.

**4. Is this relevant to SweetClaude users or only to SweetClaude itself?**  
Both — but asymmetrically. The "produce our own demo content" use case is immediate and high-value. The "SweetClaude skill for user projects" use case is redundant: `remotion-dev/skills` already exists, is first-party, and does the job. The right answer for users is "install `remotion-dev/skills` from the Remotion team" — same pattern as Skill Seekers.

**5. What are the dependencies?**  
- Node.js 18+ and npm/bun  
- FFmpeg/ffprobe — bundled since v4.0, auto-downloaded on first render  
- Puppeteer/headless Chrome — pulled in via npm  
- No Docker, no Xcode, no platform-specific build tools on macOS  
- Linux servers need additional system packages (`libgbm`, `libatk`, etc.) for headless Chrome  
- Remotion Lambda (separate package) for parallel rendering on AWS — optional

---

## License Note

Remotion uses a non-standard license. Solo developers and small projects are free. Companies above a revenue/employee threshold must purchase a commercial license. Verify current thresholds at remotion.dev/license before any commercial use.

---

## Recommendation: Use for SweetClaude's Own Demos — Do Not Build a Wrapper Skill

**Do use Remotion to produce SweetClaude's own demo content** (BL-032). The first-party Claude Code skill, low-friction setup on macOS, and documented terminal animation support make this the right tool for the job. BL-032 should proceed as a Remotion project using `remotion-dev/skills`.

**Do not build a SweetClaude wrapper skill.** The `remotion-dev/skills` package already does this, is first-party, and is better maintained than anything we'd build. Same pattern as the Skill Seekers conclusion from BL-017: point users at the authoritative source rather than duplicating it. Add a note to the user guide or marketplace listing: "For video and animation projects, install the official Remotion skill from `remotion-dev/skills`."

**No new backlog items required.** BL-032 (Remotion demo video) is the natural follow-on. The marketplace listing (BL-039) should mention Remotion in the "bringing your own context skills" framing alongside Skill Seekers.
