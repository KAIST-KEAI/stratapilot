# 🤖 How to Contribute to Stratapilot

Thanks for your interest in contributing to **Stratapilot**! Whether you're here to fix a bug, build an MCP adapter, or write a custom workflow, we’re thrilled to have your support.

Let’s get started. 🛠️

## 1. 🔀 Create a Branch

Start by branching off `main` to isolate your changes. Use a descriptive name for your feature or fix.

```bash
git checkout -b feature/your-feature-name
```

## 2. ✍️ Make Your Changes

Here’s where the magic happens. You can:
- Build a custom **MCP adapter** for a third-party app
- Add new **Stratapilot SDK modules** or workflow templates
- Improve logging, task execution, or inference logic
- Patch a bug or improve system integration
- ... or any idea you may have that can make the project better

> MCP adapters should avoid hardcoding behavior—favor structured descriptors and composability.

## 3. ✅ Run and Write Tests

Please test your changes! Use our test suite or write new cases if you're introducing features.

```bash
pytest -s tests/
```

## 4. 🧼 Check Formatting

We use `black` for consistent formatting. Run this before submitting:

```bash
poetry run black . -l 120
```

Or with pip:
```bash
black . -l 120
```

## 5. 🚀 Submit a Pull Request

You’re almost there! Time to share your brilliance:

1. Push your branch to GitHub:
    ```bash
    git push origin feature/your-feature-name
    ```
2. Head to the [Stratapilot repository](https://github.com/KAIST-KEAI/stratapilot).
3. Open a **Pull Request** from your feature branch into `main`.
4. Include:
    - A concise title
    - A clear description of what you changed and *why*
    - (Optional) Screenshots, test output, or example usage if relevant

## 6. 👀 Review & Collaboration

Our maintainers will review your submission. We may suggest changes, request clarification, or invite you to expand the feature further. Once approved, your contribution becomes part of Stratapilot!

Thanks again for helping build a smarter, more capable operating system agent.  
We’re glad to have you with us. 💚
