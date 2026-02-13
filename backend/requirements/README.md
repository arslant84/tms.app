# TMS Backend Requirements

This directory contains environment-specific requirement files for the TMS backend application.

## Files

- **base.txt** - Core dependencies required in all environments
- **development.txt** - Additional tools for local development and testing
- **production.txt** - Production-specific packages (WSGI server, monitoring, caching)

## Installation

### Development Environment

```bash
pip install -r requirements/development.txt
```

This installs all base dependencies plus development tools like:
- Django Debug Toolbar
- Testing frameworks (pytest, pytest-django)
- Code quality tools (flake8, black, isort)
- API documentation (drf-spectacular)

### Production Environment

```bash
pip install -r requirements/production.txt
```

This installs all base dependencies plus production tools like:
- Gunicorn (WSGI server)
- WhiteNoise (static file serving)
- Sentry (error tracking)
- Redis & django-redis (caching)

## Updating Requirements

### Adding a new dependency

1. Determine which file it belongs in:
   - **base.txt** - Required for the app to run
   - **development.txt** - Only needed for development/testing
   - **production.txt** - Only needed in production

2. Add the package with version constraint:
   ```
   package-name>=x.y.z
   ```

3. Update your virtual environment:
   ```bash
   pip install -r requirements/development.txt
   ```

4. Commit the changes to version control

### Generating exact versions (optional)

To freeze exact versions for reproducible builds:

```bash
# After installing requirements
pip freeze > requirements/frozen-$(date +%Y%m%d).txt
```

## Migration from old requirements.txt

The original `requirements.txt` has been split into these three files. If you need to reference the old file, it should remain in the backend root for backward compatibility until all deployment scripts are updated.

## Notes

- All requirements files use `-r base.txt` to inherit base dependencies
- Version constraints use `>=` to allow patch updates while preventing breaking changes
- Production requirements include performance and monitoring tools
- Development requirements include testing and code quality tools
