# Competitive research: ChatGPT, Gemini and the GenUI field

> Summarised from `../../Synapse-V4/refdocs/evidence/2026-11-01-speed-visual-deploy-research.md`, `2026-10-21-chatgpt-intelligent-ui-rea.md`, the owner's `../../research/generative-ui-research-2026-07-06.md`, and searches on 2026-11-09. Nothing here comes from a live GPT-6 session. Evidence quality is marked.

## 1. ChatGPT Intelligent UI (OpenAI, launched 7 October 2026 with GPT-6)

| Aspect | What is known | Evidence |
|---|---|---|
| What it is | Answers combine text, graphics, buttons, forms, charts and small tools. The format is chosen per question, and stays text when text is best | OpenAI release notes, press |
| How it is built | A library of native, streamable components plus a compiler that renders the interface while the model is still writing | Press, attributed to OpenAI |
| Inside | The model writes "DIL" (Markdown, JSX-like catalogue tags, JS state); the server repairs and compiles each partial reply; a sandboxed iframe and web worker run it; about 70 components; an `AppBlock` escape hatch for model-written HTML; UI actions start a new turn from the UI's state | **One competitor's reverse engineering (Thesys), unverified** |
| Speed claim | "44 percent sooner" to *start* a web-search answer. No figure for a finished interface | OpenAI, press |
| Quality | Trained and graded for clarity, usefulness and completeness. OpenAI: "work ahead to improve the model's design judgment" | OpenAI, via press |
| Correctness | No public check of generated content. Press advises users to verify figures | Absence in sources |
| Learning visuals (March 2026) | A set list of 70+ concepts, including Hooke's law and Ohm's law | OpenAI post |

## 2. Gemini generative UI (Google)

| Aspect | What is known |
|---|---|
| How it is built | Gemini 3 Pro writes a full custom page, with tools (image generation, search), detailed system instructions and post-processing |
| Framing | Users get tailored interfaces "rather than having to select from an existing catalog of applications" |
| Speed | Quality results are stated "when ignoring generation speed"; Google's earlier write-up said "a minute or more" |
| Wait handling | Status messages and thinking steps |
| A2UI protocol | Declarative JSON UI from a trusted catalogue, streamed progressively; v0.9 added a React renderer and a Python agent SDK (secondary sources, 2026) |

## 3. The wider GenUI field (owner's taxonomy)

| Level | Systems | Synapse v5 |
|---|---|---|
| 1: catalogue components | Vercel AI SDK RSC, OpenAI Apps SDK | Kit parts |
| 2: declarative UI | Thesys C1 and OpenUI Lang (streaming parser, about 67 percent fewer tokens than JSON, vendor claim), Google A2UI, Vercel json-render | Build Script's declarative sections and formulas |
| 3: generated code | Gemini dynamic view, Claude artifacts, CopilotKit Open Generative UI (streams HTML into an `allow-scripts` iframe, morphed with Idiomorph) | Build Script's DRAWING and SCRIPT, checked |
| Editing | MAIC-UI (Tsinghua, 2026): diff edits instead of 200 to 600 s full regeneration | Change this environment |

## 4. Where Synapse v5 stands

| | ChatGPT | Gemini | Synapse v4 | Synapse v5 (planned) |
|---|---|---|---|---|
| Interface appears while written | Yes | Status only | No | Yes (forming environment) |
| Follow-up changes the interface | Reported | Not checked | No | Yes (patch) |
| Correctness checked | Not public | Post-processors | Yes | Yes, per part |
| Textbook citations | No | No | Yes | Yes |
| Hands-on apparatus | Some | Varies | Yes | Yes |
| Domain and syllabus | General | General | KSSM science only | Any domain; curriculum packs (KSSM and Bahasa Melayu first) |
| Time to a finished interactive | Not published | "a minute or more" (earlier) | 24 s Kit, about 4 min generated | 35 s p50 (TARGET) |

**The pitch line:** "Ask anything. We build the experiment, then we tell you exactly how far it was checked."

## Sources

- [OpenAI: new ways to learn math and science](https://openai.com/index/new-ways-to-learn-math-and-science-in-chatgpt)
- [TechRepublic: GPT-6 Intelligent UI](https://www.techrepublic.com/article/news-gpt-6-intelligent-ui-charts-forms/)
- [TechCrunch: Intelligent UI launch](https://techcrunch.com/2026/10/07/chatgpt-is-getting-a-lot-more-visual-with-the-launch-of-a-new-interface/)
- [Wikidocs: detailed summary of OpenAI's announcement](https://wikidocs.net/blog/@jaehong/32854/)
- [OpenUI (Thesys): how Intelligent UI works, unverified](https://www.openui.com/blog/how-chatgpt-intelligent-ui-works)
- [Google Research: Generative UI](https://research.google/blog/generative-ui-a-rich-custom-visual-interactive-user-experience-for-any-prompt/)
- [MLOps Community: from AI-orchestrated development to A2UI](https://home.mlops.community/home/blogs/finding-the-holy-grail-of-ai-agent-uis-from-ai-orchestrated-development-to-a2ui)
- [MAIC-UI paper, arXiv 2604.25806](https://arxiv.org/abs/2604.25806)
- [CopilotKit: Open Generative UI](https://docs.copilotkit.ai/generative-ui/open-generative-ui)
- [OpenUI lang-core README](https://cdn.jsdelivr.net/npm/@openuidev/lang-core@0.2.6/README.md)
- [Semantic caching thresholds, Portkey](https://portkey.ai/blog/semantic-caching-thresholds/)
- [Semantic caching correctness, arXiv 2502.03771](https://arxiv.org/pdf/2502.03771.pdf)
- [Playwright for Python: Clock](https://playwright.dev/python/docs/clock)
