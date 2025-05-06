# Dependency Constraints for Traffic Violation System

This document tracks known dependency constraints and conflicts encountered during deployment.

## Critical Constraints

| Package | Constraint | Reason | Status |
|---------|------------|--------|--------|
| reportlab | Must use v3.6.x | `xhtml2pdf 0.2.11` requires `reportlab<4 and >=3.5.53` | Fixed in requirements-fixed.txt (3.6.13) |
| pyparsing | Must use v3.0.9 | Avoids conflicts with matplotlib and other packages | Fixed in all requirements files |
| pyhanko-certvalidator | Must use v0.20.0 | Required by pyHanko==0.17.0 and must be installed first | Fixed in requirements order |
| idanalyzer | Must use v1.2.2 | Latest version that's compatible with our codebase | Implemented graceful degradation |
| Python | Must use v3.10.0 | Needed for contourpy and other dependencies | Updated in render.yaml |

## Handling Strategy

The project uses a multi-tier approach to handle dependency conflicts:

1. **Fixed Requirements**: `requirements-fixed.txt` with carefully specified versions
2. **Fallback Mechanisms**: Multiple requirements files and individual package installation
3. **Graceful Degradation**: Fallback implementations for problematic modules
4. **Direct Import Patching**: Runtime modifications to handle import errors

## Fallback Order

When resolving dependencies, the build script attempts:

1. Install from `requirements-fixed.txt`
2. If that fails, try `requirements.txt`
3. If that fails, try `requirements-minimal.txt`
4. Install critical packages individually with specific versions

## Adding New Dependencies

When adding new dependencies:

1. Add to `requirements.txt` first
2. Test locally for conflicts
3. If conflicts arise:
   - Add compatible version to `requirements-fixed.txt`
   - Update `requirements-minimal.txt` if needed
   - Update the build script for fallback scenarios
   - Consider adding graceful degradation if the module may fail to import

## Testing Dependencies

To verify dependency resolution:

```bash
# Create a clean virtual environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Try installing dependencies
pip install -r requirements-fixed.txt

# If issues occur, check for conflicts
pip check

# Test individual packages
pip install reportlab==3.6.13
pip install xhtml2pdf==0.2.11
``` 