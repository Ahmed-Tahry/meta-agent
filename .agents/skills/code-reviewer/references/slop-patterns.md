# Slop Pattern Reference

Detailed detection rules for each AI-slop category.

---

## REDUNDANT_COMMENT

**Definition**: A comment that says exactly what the next line of code says.
A human reading the code would gain zero information from it.

**Detect**:
- Comment verb matches function name: `# initialize client` above `client = Client()`
- Comment restates the assignment: `# set x to 5` above `x = 5`
- Every function has a comment, even trivial ones
- Inline comments on obvious operations: `i += 1  # increment i`

**Fix**: Delete. No replacement needed.

**Keep if**: The comment explains *why* a non-obvious value is used, or documents a
non-obvious side effect.

---

## SYCOPHANTIC_DOCSTRING

**Definition**: Docstring that compliments the function, uses marketing language,
or is written in a tone that implies the author is proud of it.

**Detect**:
- "This function efficiently..."
- "This powerful method..."
- "This comprehensive implementation..."
- "Handles all edge cases gracefully"
- "Robust and scalable..."
- Length >> actual content (3-line docstring for a 2-line function)

**Fix**: Delete the docstring entirely, OR replace with a single factual sentence
describing the return value and side effects only.

---

## DEAD_SCAFFOLDING

**Definition**: Code structure with no operational content — exists because the LLM
scaffolded it "just in case."

**Detect**:
- `try: ... except: pass` with no logging or re-raise
- `except Exception as e: print(e)` with no recovery
- Empty `__init__` methods
- Functions that only call one other function with the same arguments
- Abstract base classes with 1 concrete subclass and no foreseeable variation
- Stub functions: `def process(): # TODO: implement`
- Unused class attributes set in `__init__` and never read

**Fix**:
- Empty try/except: remove the try block, let exceptions propagate
- Wrapper functions with no logic: inline the call at callsite
- Abstract base with 1 subclass: collapse to concrete class directly
- Stubs: keep only if they're wired into an interface that needs them; flag otherwise

---

## HALLUCINATED_IMPORT

**Definition**: Import of a package or module that doesn't exist in the project's
dependency manifest, or that the LLM invented.

**Detect**:
- Import not in `requirements.txt`, `package.json`, `go.mod`, `pom.xml`
- Package name that sounds plausible but doesn't exist on PyPI/npm: `import datautils`
- Importing a symbol that doesn't exist in a real package: `from requests import AsyncClient`

**Fix**:
1. Check if the package exists in the manifest
2. If not, check PyPI/npm for the real package name
3. If the package exists but symbol doesn't: find the real symbol name
4. If entirely hallucinated: remove the import and all callsites, flag for human

---

## COPY_PASTE_DUPLICATION

**Definition**: Blocks of logic that are near-identical across multiple files/functions,
differing only in variable names or minor literals.

**Detect**:
- Same 5+ line pattern appearing 3+ times
- Multiple files with nearly identical `__init__` / constructor logic
- Parallel service classes with identical method signatures but slightly different names

**Fix**: Extract shared logic into a utility function or base class with parameters.
Only do this if the duplication is clearly unintentional — domain-required repetition
(e.g., two separate business rules that happen to look similar) should be flagged, not merged.

---

## VERBOSE_NAME

**Definition**: Function, variable, or class names that are longer than needed to
convey their meaning — often read like a sentence.

**Detect**:
- Function names with >4 words: `get_all_available_payment_records_from_database()`
- Variables that restate type: `user_list_array`, `config_dict_object`
- Names with redundant context: `UserService.get_user_by_user_id(user_id)` (the `by_user_id` is redundant — what else would you get a user by?)

**Fix**: Shorten to the minimal unambiguous name.
- `get_all_available_payment_records_from_database()` → `fetch_payments()`
- `user_list_array` → `users`
- `get_user_by_user_id(user_id)` → `get_user(user_id)`

**Language note**: Some frameworks enforce verbose naming (Django, Spring). Don't rename
framework-convention names.

---

## DEFENSIVE_OVERLOAD

**Definition**: Null/type checks, guards, and assertions applied to values that provably
cannot be null/wrong at that point, or that are type-safe by construction.

**Detect**:
- `if user is None: raise ValueError("user is None")` — immediately after `user = get_user()` which already raises on not-found
- Redundant isinstance checks on typed parameters in a typed language
- `assert isinstance(x, int)` on a value just returned from `int(input)`
- Double null checks: `if x: if x is not None:`

**Fix**: Remove the redundant guard. Keep guards that protect against real external uncertainty (user input, network responses, config files).

---

## FAKE_LOGGING

**Definition**: Log statements that carry no actionable information — they exist because
the LLM adds them by default.

**Detect**:
- `logger.info("Starting process...")` with no context about *which* process or *for what*
- `logger.info("Done.")` with no indication of what completed
- `logger.debug("Entering function X")` — function name adds nothing to a stack trace
- Logging every step of a loop with no per-iteration data
- Log message duplicates the function name

**Fix**: Delete. If logging is needed, replace with a message that includes: *what* happened, *which entity*, and *relevant identifiers* (IDs, counts, durations).

**Good logging**: `logger.info("Payment processed", extra={"payment_id": p.id, "amount": p.amount, "ms": elapsed})`

---

## OVER_ENGINEERED

**Definition**: Abstraction layers, design patterns, or infrastructure that is more
complex than the problem warrants — added because LLMs default to "enterprise patterns."

**Detect**:
- Factory class that creates one type of object
- Strategy pattern with one strategy
- Repository pattern over a single table with 3 queries
- Config class that wraps `os.getenv` with no validation
- Event bus / pub-sub for two communicating components
- Dependency injection container for a script with no tests
- Abstract interfaces with a single implementation and no tests mocking it

**Fix**: Collapse to direct code. Replace `PaymentProcessorFactory.create("stripe")` with `StripeProcessor()` if there's only one processor.

**Keep if**: There's a documented plan for variation, it's wired into a test suite, or it's a framework requirement.

---

## STRUCTURAL_BLOAT

**Definition**: Functions that are split into tiny sub-functions for no reason,
or deeply nested structures that could be flat.

**Detect**:
- Helper functions that are called once and whose entire body would fit inline
- 3-level class inheritance for non-polymorphic logic
- Module split into 8 files where 1 would read better
- `main()` that does nothing but call `run()` that does nothing but call `execute()`

**Fix**: Inline single-use helpers. Flatten inheritance where no polymorphism exists.

---

## INCONSISTENT_STYLE

**Definition**: Mixed conventions within a single file or tightly related module group.

**Detect**:
- camelCase and snake_case in same Python file
- `async/await` and `.then()` chains mixed in same TS file
- Some functions have docstrings, others don't (no clear rule)
- Inconsistent quote style within a file (not enforced by formatter)
- Mix of f-strings and `.format()` in same file

**Fix**: Normalize to the dominant convention in the file. If no dominant convention,
use the language's official style guide (PEP 8, Google TS style, etc.).
