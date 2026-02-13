# Stylelint Setup Instructions

## Installation

To enable stylelint for enforcing design system usage, run:

```bash
npm install --save-dev stylelint stylelint-config-standard-scss stylelint-config-recommended stylelint-scss
```

## Package.json Scripts

Add these scripts to your `package.json`:

```json
{
  "scripts": {
    "lint:styles": "stylelint \"src/**/*.scss\"",
    "lint:styles:fix": "stylelint \"src/**/*.scss\" --fix",
    "lint:all": "npm run lint:styles"
  }
}
```

## Usage

```bash
# Check for style violations
npm run lint:styles

# Auto-fix violations where possible
npm run lint:styles:fix
```

## Configuration

The `.stylelintrc.json` file is already configured and will:
- Enforce SCSS best practices
- Warn about hardcoded values (to be enhanced)
- Support Angular-specific selectors (::ng-deep, :host, etc.)
- Ignore build artifacts and node_modules

## Note

Stylelint configuration is ready. Install the packages when ready to enforce linting rules.
