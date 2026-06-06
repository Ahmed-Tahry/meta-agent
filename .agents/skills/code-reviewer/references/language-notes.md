# Language-Specific Slop Notes

Additional patterns beyond the general ones in `slop-patterns.md`.

---

## Python

- **`type: ignore` abuse** — LLMs scatter these to silence mypy. Flag every one; most can be fixed properly.
- **`*args, **kwargs` everywhere** — Added defensively when the LLM wasn't sure about the signature. Flag if the function has a fixed call site.
- **Unnecessary ABC** — `class MyService(ABC)` with `@abstractmethod` but only one subclass. Collapse to plain class.
- **`__all__` that lists everything** — Defeats the purpose. Either curate it or remove it.
- **`if __name__ == "__main__"` wrapping a single function call** — Fine to keep, but flag if the function is also callable from tests and has side effects.
- **Overuse of `dataclass`** — LLMs default to dataclasses for everything. A plain dict or namedtuple may suffice for internal-only data.
- **`Optional[X]` on non-optional values** — Added "just in case". Check actual call sites.

---

## TypeScript / JavaScript

- **`any` type** — Almost always unnecessary. Flag every occurrence.
- **`// @ts-ignore`** — Same as `type: ignore`. Flag and fix.
- **Redundant `interface` + `type` alias for same shape** — LLMs often define both.
- **`.then().catch()` chains alongside `async/await`** — Pick one per file.
- **`React.FC<Props>`** — Outdated pattern; unnecessary wrapper type. Use plain function signatures.
- **`useEffect` with empty deps `[]` that contains async logic** — Common LLM anti-pattern; creates race conditions.
- **Unnecessary `useMemo`/`useCallback`** — LLMs add these defensively. Remove if the dependency is trivially cheap.
- **`console.log` left in** — Always flag; replace with proper logger or remove.
- **`export default` + named export for same thing** — Pick one.

---

## Go

- **`interface{}` / `any` overuse** — Defeats Go's type system. Flag if a concrete type is known.
- **Goroutine for trivial serial tasks** — `go func() { result = doThing() }()` on something that needs the result immediately.
- **Error wrapping without context** — `return err` instead of `return fmt.Errorf("context: %w", err)`.
- **Huge `init()` functions** — LLMs stuff initialization logic here. Should be explicit.
- **Unused struct fields** — Added "for future use". Remove unless there's a migration reason.

---

## Java / Kotlin

- **God-class `@Service`** — Single service class with 30+ methods covering unrelated domains.
- **Lombok over-use** — `@Data` on a class that should be immutable (use `@Value`) or has custom equals logic.
- **`Optional.get()` without `isPresent()`** — Classic LLM mistake; will throw at runtime.
- **Design pattern overload** — Builder + Factory + Singleton for a simple config object.
- **`@SuppressWarnings("unchecked")`** — Almost always fixable with proper generics.

---

## Rust

- **`.unwrap()` everywhere** — LLMs use it to silence the compiler. Every `.unwrap()` should be `?`, `expect("reason")`, or a proper match.
- **Cloning to avoid lifetime reasoning** — Flag excessive `.clone()` calls; most can be removed with proper borrows.
- **`Box<dyn Trait>` when concrete type is known** — Dynamic dispatch added unnecessarily.
