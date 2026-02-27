

---

# 🚀 Development Workflow Guide

*(Team-A Receipt & Invoice Digitizer)*

---

## ✅ After Successful Project Setup

Once the project runs successfully using:

```bash
streamlit run app.py
```

Follow the steps below for development and pushing code.

---

# 🔁 1. Always Sync With Main Branch First

Before starting any work:

```bash
git checkout main
git pull origin main
```

This ensures your local repository is up to date.

---

# 🌿 2. Create a New Feature Branch

Never work directly on `main`.

Create a new branch for your assigned module:

```bash
git checkout -b feature/<your-feature-name>
```

Examples:

```bash
git checkout -b feature/analytics
git checkout -b feature/ui-dashboard
git checkout -b feature/charts
git checkout -b feature/reporting
```

---

# 💻 3. Start Coding

* Work only inside your assigned module.
* Keep commits small and meaningful.
* Test your changes locally before pushing.

Run the app to verify:

```bash
streamlit run app.py
```

---

# 💾 4. Stage and Commit Changes

After completing a logical unit of work:

```bash
git add .
git commit -m "Implemented monthly spending analytics"
```

Commit message should clearly describe what you did.

---

# 🚀 5. Push Branch to GitHub

Push your feature branch:

```bash
git push -u origin feature/<your-feature-name>
```

Example:

```bash
git push -u origin feature/analytics
```

---

# 🔄 6. Create a Pull Request (PR)

1. Go to GitHub repository.
2. Click **Compare & Pull Request**.
3. Select:

   * Base branch → `main`
   * Compare branch → `feature/your-branch`
4. Add proper description of changes.
5. Submit PR.

---

# 👀 7. Code Review

* Team members review changes.
* Suggest improvements if needed.
* Once approved → merge into `main`.

---

# 🔁 8. After Merge

Switch back to main and update:

```bash
git checkout main
git pull origin main
```

Delete old branch locally if needed:

```bash
git branch -d feature/<your-feature-name>
```

---

# ⚠️ Important Rules

* ❌ Do NOT push directly to `main`
* ❌ Do NOT commit `.db` files
* ❌ Do NOT commit raw image datasets
* ❌ Do NOT overwrite someone else's branch
* ✅ Always pull latest main before creating new branch
* ✅ Use clear branch names
* ✅ Use meaningful commit messages

---

# 📌 Recommended Branch Naming

```
feature/analytics
feature/ui
feature/charts
feature/reporting
bugfix/<issue-name>
refactor/<module-name>
```

---

# 🧠 Professional Workflow Summary

1. Pull latest main
2. Create feature branch
3. Code & test
4. Commit changes
5. Push branch
6. Create PR
7. Review & merge
8. Sync main again

---

This workflow ensures:

* No merge conflicts
* Clean version history
* Professional collaboration
* Scalable team development

---


