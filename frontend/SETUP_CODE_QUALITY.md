# Code Quality Tools Setup

This project uses ESLint, Prettier, and Stylelint for code quality and formatting.

## Installation

The configuration files are already in place. To install the required packages, run:

```bash
npm install --save-dev @angular-eslint/builder @angular-eslint/eslint-plugin @angular-eslint/eslint-plugin-template @angular-eslint/schematics @angular-eslint/template-parser @typescript-eslint/eslint-plugin @typescript-eslint/parser eslint prettier
```

Or install them individually:

```bash
# ESLint and Angular ESLint
npm install --save-dev eslint @typescript-eslint/eslint-plugin @typescript-eslint/parser
npm install --save-dev @angular-eslint/builder @angular-eslint/eslint-plugin @angular-eslint/eslint-plugin-template @angular-eslint/schematics @angular-eslint/template-parser

# Prettier
npm install --save-dev prettier
```

## Usage

### Linting

```bash
# Lint TypeScript files
npm run lint:ts

# Lint TypeScript files and auto-fix
npm run lint:ts:fix

# Lint SCSS files
npm run lint:scss

# Lint SCSS files and auto-fix
npm run lint:scss:fix

# Lint everything (TypeScript + SCSS)
npm run lint
```

### Formatting

```bash
# Format all files
npm run format

# Check formatting without making changes
npm run format:check
```

## IDE Integration

### VS Code

Install these extensions:
- ESLint (`dbaeumer.vscode-eslint`)
- Prettier (`esbenp.prettier-vscode`)
- Stylelint (`stylelint.vscode-stylelint`)

Add to `.vscode/settings.json`:

```json
{
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true,
    "source.fixAll.stylelint": true
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[html]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[scss]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

### WebStorm / IntelliJ IDEA

1. Enable ESLint:
   - Settings → Languages & Frameworks → JavaScript → Code Quality Tools → ESLint
   - Select "Automatic ESLint configuration"
   - Check "Run eslint --fix on save"

2. Enable Prettier:
   - Settings → Languages & Frameworks → JavaScript → Prettier
   - Set Prettier package to `node_modules/prettier`
   - Check "On save"

3. Enable Stylelint:
   - Settings → Languages & Frameworks → Style Sheets → Stylelint
   - Check "Enable"

## Configuration Files

- `.eslintrc.json` - ESLint configuration for TypeScript and Angular
- `.prettierrc` - Prettier formatting rules
- `.prettierignore` - Files to ignore from formatting
- `.stylelintrc.json` (already exists) - Stylelint SCSS rules

## Pre-commit Hooks (Optional)

To enforce code quality before commits, install Husky and lint-staged:

```bash
npm install --save-dev husky lint-staged

# Initialize Husky
npx husky install

# Add pre-commit hook
npx husky add .husky/pre-commit "npx lint-staged"
```

Add to `package.json`:

```json
{
  "lint-staged": {
    "*.ts": [
      "eslint --fix",
      "prettier --write"
    ],
    "*.html": [
      "prettier --write"
    ],
    "*.scss": [
      "stylelint --fix",
      "prettier --write"
    ]
  }
}
```

## Notes

- **ESLint**: Enforces code quality rules and catches potential bugs
- **Prettier**: Enforces consistent code formatting
- **Stylelint**: Enforces SCSS/CSS best practices
- The configurations are set to warn (not error) for most issues to avoid blocking development
- Run `npm run lint` before committing to catch issues early
