# Mockup Generation - Detailed Steps

## Purpose
**Visualize requirements before user stories to validate direction and build team alignment**

Mockup Generation focuses on:
- Translating abstract requirements into concrete visual artifacts
- Validating project direction early (before user stories are written)
- Building shared understanding across the team through visual artifacts
- Providing interactive prototypes that stakeholders can experience hands-on
- Surfacing implicit assumptions before they propagate into stories and code

## Prerequisites
- Workspace Detection must be complete
- Requirements Analysis must be complete
- User Stories stage must NOT have started yet
  - ⚠️ **IMPORTANT**: If User Stories or any later stage has already been executed, Mockup Generation does NOT apply retroactively. Continue with the existing workflow.

## Intelligent Assessment Guidelines

**WHEN TO EXECUTE MOCKUP GENERATION**:

### Execute IF (any of the following applies)
- Application has a **user interface** (web, mobile, desktop, embedded UI)
- Multiple user touchpoints or screens exist
- User journey spans 3+ interaction steps
- User experience is central to the product value
- Team needs shared visual understanding before implementation
- Stakeholders include non-technical members who benefit from visual artifacts
- Requirements are complex or ambiguous enough that visualization reduces risk

### Skip IF (all of the following apply)
- Backend API only (no user-facing interface)
- CLI tools without interactive flows worth visualizing
- Infrastructure/DevOps changes only
- Pure code refactoring with no user-facing impact
- Library/SDK development without reference UI

### Default Decision Rule
**When in doubt, execute.** The cost of a lightweight mockup is lower than the cost of writing stories that miss the user experience entirely.

---

# PART 1: PLANNING

## Step 1: Validate Mockup Generation Need (MANDATORY)

### Assessment Process
1. **Analyze Request Context**:
   - Review the requirements document
   - Identify whether the project has a user interface or user-facing interaction
   - Assess complexity of user flows
   - Evaluate team alignment needs

2. **Determine Project Type** (drives mockup format selection in Step 3):
   - **UI-centric**: Web/mobile/desktop apps with screens → full mockup suite + HTML prototype
   - **CLI-centric**: Command-line tools with interactive dialog → command transcripts + journey
   - **API-centric**: Backend services with external consumers → request/response examples + sequence diagrams
   - **Infrastructure-centric**: Deployment, pipelines → data flow diagrams + component diagrams
   - **Hybrid**: Combination of above

3. **Document Assessment Decision**:
   - Create `aidlc-docs/inception/plans/mockup-assessment.md`
   - Record project type, rationale, and expected artifacts

### Assessment Documentation Template
```markdown
# Mockup Generation Assessment

## Request Analysis
- **Original Request**: [Brief summary]
- **User Interface**: [Yes / No]
- **Project Type**: [UI-centric / CLI-centric / API-centric / Infrastructure-centric / Hybrid]
- **User Touchpoints**: [Count and brief description]
- **Stakeholders**: [List involved parties]

## Assessment Criteria Met
- [ ] Execute criteria: [List applicable criteria]
- [ ] Expected benefits: [Direction validation / Team alignment / Risk reduction]

## Decision
**Execute Mockup Generation**: [Yes / No]
**Reasoning**: [Detailed justification]

## Mockup Format Plan
- [ ] Text artifacts (mockup.md, screen-flow.md, user-journey.md, mockup-review-questions.md)
- [ ] Interactive HTML prototype (html/) — for UI-centric or Hybrid projects
- [ ] Mermaid diagrams for flows
```

## Step 2: Create Mockup Plan
- Assume the role of a **UX designer + product owner hybrid**
- Generate a comprehensive plan with step-by-step execution checklist
- Each step and sub-step should have a checkbox `[ ]`
- Focus on methodology for visualizing requirements without premature commitment to visual design details

## Step 3: Generate Context-Appropriate Questions

**DIRECTIVE**: Analyze requirements thoroughly to identify ALL areas where visualization choices would benefit from clarification.

**CRITICAL**: Default to asking questions when there is ANY ambiguity in visual direction, screen inventory, or user flow coverage.

**See `common/question-format-guide.md` for question formatting rules**

- EMBED questions using `[Answer]:` tag format
- Label multiple-choice options A, B, C, D, etc.
- Always include an "Other (please describe)" option

**Question categories to evaluate**:

- **Screen Inventory**: Ask which screens/views are in scope, which are deferred, which are optional
- **Fidelity Level**: Ask preferred fidelity — Lo-fi (ASCII wireframes) / Mid-fi (HTML + basic styling) / Hi-fi (HTML + polished CSS)
- **Interaction Depth**: Ask which interactions must be experienceable in the HTML prototype (navigation only / form input / dynamic feedback / full flow)
- **Persona Coverage**: Ask which personas' journeys must be illustrated (primary only / all personas / happy + edge case)
- **Flow Coverage**: Ask which flows are mandatory (onboarding / main action / error / recovery / exit)
- **Visual Vocabulary**: Ask preferred style direction (minimalist / branded / playful) — only if affects validation
- **Accessibility Targets**: Ask target accessibility level (none specified / informal / WCAG AA awareness)
- **Platform Targets**: Ask target platforms (desktop web / mobile web / native iOS / native Android / responsive)
- **Language for UI Copy**: Ask preferred language for UI labels and copy in the prototype

## Step 4: Include Mandatory Mockup Artifacts in Plan

- **ALWAYS** include these mandatory artifacts in the mockup plan:
  - [ ] Generate `aidlc-docs/inception/mockup/mockup.md` with screen inventory, element lists, and ASCII wireframes for each screen
  - [ ] Generate `aidlc-docs/inception/mockup/screen-flow.md` with Mermaid flowchart showing navigation between screens
  - [ ] Generate `aidlc-docs/inception/mockup/user-journey.md` with Mermaid sequence/flowchart per persona
  - [ ] Generate `aidlc-docs/inception/mockup/mockup-review-questions.md` with generic UX review questions using `[Answer]:` tags
  - [ ] Generate `aidlc-docs/inception/mockup/html/` interactive prototype (UI-centric projects: MANDATORY; others: skip or provide minimal)
  - [ ] Ensure every requirement in requirements.md has at least one corresponding mockup element (traceability)
  - [ ] Ensure every persona has at least one journey diagram

## Step 5: Present Mockup Approach Options

Include different approaches for mockup breakdown in the plan:

- **Screen-Driven**: Start from screen inventory, then derive flows
- **Flow-Driven**: Start from user journeys, then materialize screens
- **Requirement-Driven**: Start from requirements traceability, then build visuals per requirement
- **Persona-Driven**: Build one complete journey per persona first

Explain trade-offs and allow hybrid approaches.

## Step 6: Interactive HTML Prototype Specification

**For UI-centric and Hybrid projects**, the HTML prototype is MANDATORY. Specify:

### Technical Constraints (NON-NEGOTIABLE)
- **Zero external dependencies**: No CDN, no package manager, no framework. Vanilla HTML/CSS/JS only.
- **Offline operation**: Must work when opened via `file://` in a browser. No `fetch` to external origins.
- **No tracking**: Zero analytics scripts, zero third-party beacons, zero telemetry.
- **Self-contained directory**: Everything under `html/` — no references outside this directory.
- **Security**: No hardcoded credentials, no secrets, no real API keys even in dummy form.

### Required Capabilities
- **Screen navigation**: Clicking buttons/links transitions between screens (SPA-style via JS, or linked HTML files)
- **Button/link interactions**: All primary CTAs must be clickable and visually respond
- **Form inputs** (if applicable): At minimum, text input should accept and display entered values
- **Browser-only**: User opens `html/index.html` in any modern browser and can experience the flow

### File Structure
```
html/
├── index.html      # Entry point with SPA structure or landing
├── styles.css      # Vanilla CSS, no preprocessors, no CDN
├── app.js          # Vanilla JS, screen transitions, button handlers
└── README.md       # How to open: "Double-click index.html, or run a local file server"
```

### Scope Discipline
- HTML prototype is for **direction validation**, NOT for final implementation
- Do not implement business logic beyond what's needed for experience
- Do not connect to real backends — use in-JS dummy data
- Do not optimize for production (no minification, no bundling)

## Step 7: Store Mockup Plan
- Save the complete mockup plan with embedded questions in `aidlc-docs/inception/plans/` directory
- Filename: `mockup-generation-plan.md`
- Include all `[Answer]:` tags for user input

## Step 8: Request User Input
- Ask user to fill in all `[Answer]:` tags directly in the mockup plan document
- Provide clear instructions
- Explain that all questions must be answered before proceeding

## Step 9: Collect Answers
- Wait for user to provide answers via `[Answer]:` tags in the document
- Do not proceed until ALL tags are completed

## Step 10: ANALYZE ANSWERS (MANDATORY)
Before proceeding, review all answers for:
- Vague responses (e.g., "mix of", "not sure", "depends")
- Undefined criteria or terms
- Contradictory answers
- Missing scope definitions (e.g., "standard screens" without specifying which)
- Assumption-based responses

## Step 11: MANDATORY Follow-up Questions
If Step 10 reveals ANY ambiguity:
- Create a separate clarification questions file
- Do not proceed to approval until ALL ambiguities are resolved

## Step 12: Avoid Implementation Details
- Focus on mockup methodology, not production-grade UI implementation
- Do not commit to visual brand identity at this stage (that's design phase)
- Do not create full design system tokens — rough visual cues are sufficient

## Step 13: Log Approval Prompt
- Before asking for approval, log the prompt with timestamp in `aidlc-docs/audit.md`
- Use ISO 8601 timestamp format

## Step 14: Wait for Explicit Approval of Plan
- Do not proceed until the user explicitly approves the mockup approach
- If user requests changes, update the plan and repeat the approval process

## Step 15: Record Approval Response
- Log the user's approval response with timestamp in `aidlc-docs/audit.md`

---

# PART 2: GENERATION

## Step 16: Load Mockup Generation Plan
- [ ] Read the complete mockup plan from `aidlc-docs/inception/plans/mockup-generation-plan.md`
- [ ] Identify the next uncompleted step (first `[ ]` checkbox)
- [ ] Load context and requirements for that step

## Step 17: Execute Current Step
- [ ] Perform exactly what the current step describes
- [ ] Generate mockup artifacts as specified in the plan
- [ ] Follow the approved methodology and format from Planning

## Step 18: Update Progress
- [ ] Mark the completed step as `[x]` in the mockup generation plan
- [ ] Update `aidlc-docs/aidlc-state.md` current status
- [ ] Save all generated artifacts

## Step 19: Continue or Complete Generation
- [ ] If more steps remain, return to Step 16
- [ ] If all steps complete, verify artifacts are ready for next stage
- [ ] Ensure all mandatory artifacts are generated

## Step 20: Validate Interactive HTML Prototype (UI-centric/Hybrid only)

Before completion, verify:
- [ ] `html/index.html` opens successfully in a browser from `file://`
- [ ] All primary navigation buttons are clickable and transition correctly
- [ ] No errors in browser console
- [ ] No external network requests (check Network tab)
- [ ] No hardcoded secrets or credentials
- [ ] `html/README.md` explains how to open the prototype

## Step 21: Validate Traceability
- [ ] Every functional requirement in `requirements.md` maps to at least one mockup element
- [ ] Every persona has at least one user-journey diagram
- [ ] Screen inventory in `mockup.md` is consistent with `screen-flow.md` nodes

## Step 22: Log Approval Prompt
- Log the approval prompt with timestamp in `aidlc-docs/audit.md`

## Step 23: Present Completion Message

Present completion message in this structure:

1. **Completion Announcement** (mandatory):

```markdown
# 🎨 Mockup Generation Complete
```

2. **AI Summary** (optional):
   - Format: "Mockup generation has produced [description]:"
   - List number of screens, flows, personas covered
   - Mention HTML prototype availability
   - Reference traceability coverage
   - Do NOT include workflow instructions

3. **Formatted Workflow Message** (mandatory):

```markdown
> **📋 <u>**REVIEW REQUIRED:**</u>**  
> Please examine the mockup artifacts at: `aidlc-docs/inception/mockup/`
> 
> For UI-centric projects, open `aidlc-docs/inception/mockup/html/index.html` in your browser to experience the interactive prototype.

> **🚀 <u>**WHAT'S NEXT?**</u>**
>
> **You may:**
>
> 🔧 **Request Changes** - Ask for modifications to the mockup based on your review  
> ✅ **Approve & Continue** - Approve mockup and proceed to **User Stories**

---
```

## Step 24: Wait for Explicit Approval of Generated Mockup
- Do not proceed until the user explicitly approves the generated mockup
- If user requests changes, update mockup and repeat the approval process

## Step 25: Record Approval Response
- Log the user's approval response with timestamp in `aidlc-docs/audit.md`

## Step 26: Update Progress
- Mark Mockup Generation stage complete in `aidlc-state.md`
- Update the "Current Status" section
- Prepare for transition to User Stories stage

---

# CRITICAL RULES

## Planning Phase Rules
- **CONTEXT-APPROPRIATE QUESTIONS**: Only ask questions relevant to this specific project type
- **MANDATORY ANSWER ANALYSIS**: Always analyze answers for ambiguities before proceeding
- **NO PROCEEDING WITH AMBIGUITY**: Must resolve all vague answers before generation
- **EXPLICIT APPROVAL REQUIRED**: User must approve plan before generation starts

## Generation Phase Rules
- **NO HARDCODED LOGIC**: Only execute what's written in the mockup generation plan
- **FOLLOW PLAN EXACTLY**: Do not deviate from the step sequence
- **UPDATE CHECKBOXES**: Mark `[x]` immediately after completing each step
- **USE APPROVED METHODOLOGY**: Follow the mockup approach from Planning
- **VERIFY COMPLETION**: Ensure all artifacts are complete before proceeding

## HTML Prototype Rules
- **ZERO EXTERNAL DEPENDENCIES**: No CDN, no npm, no bundler
- **OFFLINE OPERATION**: Must work from `file://`
- **NO TRACKING**: Zero analytics, zero beacons, zero telemetry
- **NO SECRETS**: No credentials, API keys, or private tokens — even in dummy form
- **SELF-CONTAINED**: Everything under `html/` directory

## Scope Rules
- **VISUALIZATION, NOT IMPLEMENTATION**: Mockup validates direction; it is not production code
- **TRACEABILITY REQUIRED**: Every requirement and persona must be represented
- **TEAM ALIGNMENT FIRST**: If the mockup doesn't build shared understanding, it has failed

## Completion Criteria
- All planning questions answered and ambiguities resolved
- Mockup plan explicitly approved by user
- All steps in mockup generation plan marked `[x]`
- All artifacts generated (mockup.md, screen-flow.md, user-journey.md, mockup-review-questions.md, html/ if applicable)
- HTML prototype validated for offline operation (UI-centric/Hybrid only)
- Traceability verified between requirements/personas and mockup artifacts
- Generated mockup explicitly approved by user
- Mockup ready for User Stories stage
