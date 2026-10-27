# Creatio C# Code Style & Architecture Guide

Non-functional rules for writing back-end C# code for Creatio: formatting, naming, architecture, error handling, logging, concurrency and documentation.

---

## 1. Formatting and file layout

### 1.1 Whitespace and braces

- **Tabs** for indentation, **CRLF** line endings.
- Namespace and type declarations: opening brace on a **new line**.
- Members (methods, constructors, properties, accessors) and statements: opening brace on the **same line** (K&R).
- An empty line follows the opening brace of a class.
- **Always use braces** for `if`/`else`/`foreach`, even for one statement.
- Short empty constructor: `public X(UserConnection uc) : base(uc) { }`.
- Long argument lists wrap with one extra indent level.

### 1.2 File skeleton

```csharp
namespace Terrasoft.Configuration.MyFeature
{
	using System;
	using System.Collections.Generic;
	using System.Linq;
	using Common.Logging;
	using Terrasoft.Common;
	using Terrasoft.Core;
	using Terrasoft.Core.Factories;

	#region Class: OrderSyncService

	/// <summary>
	/// Synchronizes orders with the external ERP.
	/// </summary>
	[DefaultBinding(typeof(IOrderSyncService))]
	internal class OrderSyncService : IOrderSyncService
	{

		#region Constants: Private

		private const string OrderKeyPrefix = "OrderSync:";

		#endregion

		#region Fields: Private

		private static readonly ILog _log = LogManager.GetLogger("OrderSync");
		private readonly UserConnection _userConnection;
		private readonly IOrderRepository _orderRepository;

		#endregion

		#region Constructors: Public

		public OrderSyncService(UserConnection userConnection, IOrderRepository orderRepository) {
			userConnection.CheckArgumentNull(nameof(userConnection));
			orderRepository.CheckArgumentNull(nameof(orderRepository));
			_userConnection = userConnection;
			_orderRepository = orderRepository;
		}

		#endregion

		#region Methods: Private

		private static string GetOrderKey(Guid orderId) => $"{OrderKeyPrefix}{orderId}";

		#endregion

		#region Methods: Public

		/// <inheritdoc />
		public void Sync(Guid orderId) {
			...
		}

		#endregion

	}

	#endregion

}
```

### 1.3 `using` directives

- Placed **inside** the namespace block.
- `System.*` first, then everything else alphabetically (`Common.Logging`, `Newtonsoft.Json`, `Terrasoft.*`).
- One namespace per file. A file holds one main type; small private nested helpers stay inside it.

### 1.4 `#region` layout

Wrap each top-level type in `#region Class: <Name>` (or `Interface: <Name>`, `Enum: <Name>`). Inside the type, group members into regions named `<Kind>: <Visibility>`, in this order:

1. `Constants: Private` / `Constants: Public`
2. `Fields: Private` → `Fields: Protected` → `Fields: Public`
3. `Constructors: Private` → `Constructors: Public`
4. `Properties: Private` → `Properties: Protected` → `Properties: Public`
5. `Methods: Private` → `Methods: Protected` → `Methods: Internal` → `Methods: Public`

Rules:
- Methods go from the **least visible to the most visible**: private helpers on top, the public API at the bottom.
- Kind names are plural and capitalized: `Methods: Public`, not `Method: public`.
- Inside a region: static members before instance members.
- Leave out empty regions.
- Explicit interface implementations go last.

### 1.5 General syntax

- `var` when the type is obvious from the right-hand side; explicit type otherwise.
- No `this.` qualifier (fields are already distinct by the `_` prefix).
- String interpolation `$"..."`, not `string.Format`, except with localizable resources (see 4.4).
- Expression-bodied members only for one-line getters and trivial methods:
  `private static string GetOrderKey(Guid id) => $"Order:{id}";`
- Object/collection initializers: `new Dictionary<string, string> { ["Key"] = value }`.
- No magic strings or numbers inside logic: lift them into `private const` (`LockKeyPrefix`, `ResultOk = "OK"`, `MaxRetryCount = 5`).

---

## 2. Naming

### 2.1 Members

| Element | Convention | Example |
|---|---|---|
| Private field (instance and static) | `_camelCase` | `_orderRepository`, `_lockAnchor`, `private static readonly ILog _log` |
| Protected readonly field | `PascalCase` | `protected readonly IOrderRepository OrderRepository;` |
| Constant | `PascalCase` | `private const string StopCommand = "CTRL:STOP";` |
| Static readonly "constant-like" key | `PascalCase` (internal/public) or `_camelCase` (private) | `internal static readonly string MessageStoreHashName` |
| Parameter / local | `camelCase`, full words | `retryOperationFactory`, `sessionLockKey` |
| Interface | `I` + noun | `IOrderRepository`, `ISessionLockProvider` |
| Generic parameter | `T`, `TResult`, `TValue` | `TResult Execute<TResult>(Func<TResult> operation)` |

### 2.2 Unit suffixes are mandatory

When a number means time or size, the name says the unit: `retryTimeoutMs`, `sessionLockTtlSec`, `ExecutionTimeLoggingThresholdSec`, `ConnectTimeoutMs`, `_pollIntervalMs`. Prefer `TimeSpan` in APIs and convert at the boundary: `TimeSpan.FromMilliseconds(retryTimeoutMs)`.

### 2.3 Type name suffixes (role-based)

| Suffix | Role |
|---|---|
| `IXxx` / `Xxx` | contract / default implementation |
| `BaseXxx` | abstract base with the shared algorithm (`BaseStore`, `BaseSessionManager`) |
| `XxxFactory` | creates objects that need runtime arguments (`ThrottledExecutorFactory.Create(key, interval)`) |
| `XxxProvider` | supplies data or keys (`SessionKeysProvider`, `IDateTimeProvider`) |
| `XxxStore` / `XxxRepository` | persistence |
| `XxxManager` | owns the lifecycle of resources (`ClientsManager`) |
| `XxxExecutor` | runs a delegate with a policy (`RetriableExecutor`, `ThrottledExecutor`) |
| `XxxAdapter` | wraps a third-party library behind a platform interface |
| `XxxMonitor`, `XxxValidator`, `XxxNotifier`, `XxxSynchronizer`, `XxxTerminator` | single-purpose services |
| `XxxContext` | immutable parameter object (`SessionExpiredSoonNotifierContext`) |
| `XxxOptions`, `XxxConfigSection` | configuration |
| `XxxLog` | static holder of a named logger (`OrderSyncLog`) |
| `XxxExtensions` | `static class` with extension methods |
| `DummyXxx`, `XxxMock` | no-op implementation (`DummyMetricReporter`) |
| `XxxFeatures` | container class for feature-toggle metadata |

### 2.4 Method name prefixes

| Prefix | Meaning |
|---|---|
| `Get` / `Set` / `Remove` / `Create` | basic operations |
| `GetIs` / `Is` / `Exists` / `Contains` | boolean queries. Prefer `GetIsXxx()` for methods: `GetIsSessionLocked`, `Features.GetIsEnabled<T>()` |
| `TryXxx` | returns `bool` and does not throw for the expected failure; result goes in `out` (`TryLockSession(..., out object id)`, `TrySet`) |
| `CheckXxx` | validates and **throws** on failure (`CheckVersion`, `CheckArgumentNull`) |
| `InitXxx` / `Initialize` | sets up state |
| `BuildXxx` | assembles a string or object |
| `SafeXxx` | wraps a call so it never throws (logs instead) |
| `XxxEventHandler` / `OnXxx` | event handlers |
| `ExecuteIfXxx` / `ExecuteWithXxx` | conditional or decorated execution |
| `XxxAsync` | every async method |

### 2.5 Storage key conventions

Cache and storage keys are colon-separated `Prefix:Id` built by one static method per key: `GetSessionKey(id) => "Session:" + id`. The prefixes live in `const` fields, ideally in one dedicated `static class XxxKeysProvider`.

---

## 3. Architecture

### 3.1 Program to interfaces, hide implementations

- Every service has an interface. The implementation is `internal`.
- Only real extension points are `public`: interfaces, abstract `BaseXxx` classes, and types instantiated by configuration.
- Interfaces are small, one per role: `ILock { bool TrySet(...); }`, `IVersionValidator { void CheckVersion(...); }`. Empty marker interfaces are acceptable (`IExpiredSessionPerformanceMonitor : IPerformanceMonitor`) to register one implementation under a more specific lifetime or binding.
- Open internals to tests and friend assemblies with `[assembly: InternalsVisibleTo("X.Tests, PublicKey=...")]` instead of making types public.

### 3.2 Dependency injection

**Constructor injection only.** All dependencies are `private readonly` fields assigned in the constructor.

**Constructor chaining for testability** — the pattern to use when a type is also created by legacy code or config:

```csharp
// Full constructor: all dependencies explicit (used by tests and DI).
internal PerformanceMonitor(ILog logger, IStopwatchFactory stopwatchFactory,
		TimeSpan executionTimeLoggingThreshold, bool enable) {
	_logger = logger ?? throw new ArgumentNullException(nameof(logger));
	_stopwatchFactory = stopwatchFactory ?? throw new ArgumentNullException(nameof(stopwatchFactory));
	...
}

// Convenience constructor: supplies production defaults.
public PerformanceMonitor(TimeSpan executionTimeLoggingThreshold)
	: this(MonitoringLog.Logger, new StopwatchFactory(), executionTimeLoggingThreshold,
		MonitoringConfigSection.Value.EnablePerformanceMonitor) { }

public PerformanceMonitor() : this(TimeSpan.Zero) { }
```

Rules: the **most complete** constructor holds the logic; the others only delegate with `: this(...)`. The full constructor is usually `internal`.

**Registration:**
- Configuration packages: `[DefaultBinding(typeof(IXxx))]` on the class, named when there are several implementations: `[DefaultBinding(typeof(ICalendarClient), Name = "Google")]`. Resolve with `ClassFactory.Get<IXxx>()` or `ClassFactory.Get<IXxx>("Name", new ConstructorArgument("userConnection", uc))`.
- Core libraries: an `internal static class XxxExtensions` with `public static IServiceCollection AddXxx(this IServiceCollection source)` that returns `source`. Stateless services and factories are `AddSingleton`; short-lived objects are `AddTransient`.
- Do not call `ClassFactory.Get` deep inside logic when the dependency can come through the constructor.

### 3.3 Abstract time, timers and the environment

Never call `DateTime.UtcNow`, `new Stopwatch()` or `new Timer()` directly in business logic. Inject abstractions:
`IDateTimeProvider` (`UtcNow`), `IStopwatchFactory` → `IStopwatch`, `ITimer`. This is what makes time-based logic (TTL, expiration, throttling) unit-testable.

### 3.4 Patterns to use

| Pattern | How to apply |
|---|---|
| **Template Method** | The base class owns the private algorithm; subclasses override `protected abstract` hooks. Derived classes stay tiny (often just a constructor and one `override`). |
| **Executor / decorator over delegates** | Cross-cutting concerns (retry, timing, throttling, resource scope) live in an executor that takes `Action` / `Func<T>`. Provide the full overload set: `Execute(Action)`, `Execute<TResult>(Func<TResult>)`, `ExecuteAsync(Func<Task>)`, `ExecuteAsync<TResult>(Func<Task<TResult>>)`. Executors compose (retry inside performance monitor). |
| **Factory** | Use when the created object needs runtime arguments or a fresh instance per call. A `delegate IClient ClientFactory()` is fine for a one-method factory. |
| **Adapter** | Third-party libraries never leak into domain code. Define an interface, implement it in a separate adapter assembly, keep type conversion in an `internal static class TypeConverter`. |
| **Lazy singleton** | `private static readonly Lazy<T> _instance = new Lazy<T>(() => new T());` + `public static T Instance => _instance.Value;`. Never use a mutable static field. |
| **Null object** | A no-op implementation (`DummyMetricReporter`) instead of `null` checks at call sites. |
| **Parameter object** | Immutable class (get-only properties set in the constructor) for 3+ related values. |
| **Explicit interface implementation** | Implement a secondary interface explicitly (`object IBucketedStore.Get(...)`) when its members would clutter the public surface. |

### 3.5 Resource scoping

Short-lived resources are taken and released inside one delegate:

```csharp
_retryOperationFactory.Create().Execute(() => {
	using (IClient client = _clientsManager.GetClient()) {
		client.Remove(key);
	}
});
```

Better: hide the boilerplate behind an executor: `_executor.Execute(client => client.Remove(key));`.

### 3.6 Configuration and feature toggles

- Read configuration once into a `static readonly` / `Lazy<T>` field (`XxxConfigSection.Value`, `GlobalAppSettings.Xxx`) or inject `IOptions<TOptions>`.
- **Validate configuration values; on invalid values log `Warn` and fall back to a documented default** — do not crash:
  `if (ttlSec < 1) { _log.Warn($"SessionLockTtlSec [{ttlSec}] is invalid. Defaulting to [{DefaultTtlSec}]"); ttlSec = DefaultTtlSec; }`
- Throw only for configuration that makes the component unusable: `ConfigurationErrorsException`, `AppConfigurationException` (wrong version, missing type).
- Feature toggles: a nested class deriving from `FeatureMetadata` inside an `XxxFeatures` container, checked with `Features.GetIsEnabled<TFeature>()`. Keep both branches (old and new behavior) working until the toggle is removed.

---

## 4. Error handling

### 4.1 Guard clauses first

Validate every injected dependency and public argument at the top of the method, using the `Terrasoft.Common` extensions:

```csharp
executor.CheckArgumentNull(nameof(executor));
key.CheckArgumentNullOrWhiteSpace(nameof(key));
channel.CheckArgumentNullOrEmpty(nameof(channel));
if (frequency <= TimeSpan.Zero) {
	throw new ArgumentOutOfRangeException(nameof(frequency));
}
```

Inline form for assignments: `_logger = logger ?? throw new ArgumentNullException(nameof(logger));`. Always use `nameof`.

### 4.2 Exception types

| Situation | Exception |
|---|---|
| null / empty argument | `ArgumentNullException` (via `CheckArgumentNull*`) |
| out-of-range value | `ArgumentOutOfRangeException` |
| object in a wrong state, broken invariant | `InvalidOperationException`, `InvalidObjectStateException` |
| bad configuration | `ConfigurationErrorsException`, `AppConfigurationException` |
| interface member not supported by this implementation | `NotImplementedException` / `NotSupportedException` |

Do not throw bare `new Exception(...)`.

### 4.3 Catch rules

- Rethrow with `throw;` (keeps the stack trace). Catching to record status, then rethrowing, is fine:
  ```csharp
  string status = "Success";
  try {
  	operation();
  } catch {
  	status = "Error";
  	throw;
  } finally {
  	stopwatch.Stop();
  	Log(operationName, status, stopwatch.Elapsed);
  }
  ```
- **Timer callbacks, background loops, pub/sub handlers, fire-and-forget tasks must never throw.** Wrap them in `try/catch (Exception ex) { _log.Error(..., ex); }`, and name the wrapper `SafeXxx`. An unhandled exception there kills the worker or the process.
- Retry only transient errors. Exclude errors that cannot succeed on retry: `Policy.Handle<Exception>(ex => !ex.IsPermissionException())`.
- Every caught exception is logged or rethrown. No empty `catch { }` that hides failures.

### 4.4 User-facing messages are localizable

Technical log messages are plain English strings. Messages that reach the user go through resources:

```csharp
string message = new LocalizableString("MyAssembly", "Exception.ParameterIsAbsent");
throw new InvalidObjectStateException(string.Format(message, "hashId"));
```

In configuration packages, use schema resources (`GetLocalizableString(...)` or the `LocalizableStrings` of the schema).

---

## 5. Logging

- Library: `Common.Logging` (`ILog`, `LogManager`).
- Get a **named** logger per subsystem, either as a static field or through a small static holder:
  ```csharp
  private static readonly ILog _log = LogManager.GetLogger("OrderSync");

  internal static class OrderSyncLog
  {
  	public static ILog Logger { get; } = LogManager.GetLogger("OrderSync");
  }
  ```
  For testability, accept `ILog` as an optional constructor parameter with a default: `_log = log ?? LogManager.GetLogger(typeof(X));`.
- **Message format:** `<Operation/Context>: <text> [<value>] [<value>]` — variable values always in **square brackets**:
  `$"Subscribed to channel [{channel}]"`, `$"PerformanceMonitor - {operationName} [{status}] [{elapsed}]"`, `$"Retry operation. RetryCount = [{retryCount}]. Sleep duration = [{duration}]."`
- Pass the exception as the **second argument**, do not interpolate it: `_log.Error("PublishError", ex);`.
- Levels:

| Level | Use for |
|---|---|
| `Error` | caught exceptions, failed operations |
| `Warn` | retries, fallbacks to defaults, degraded mode, reconnects, failed non-critical steps |
| `Info` | lifecycle: started/stopped, subscribed/unsubscribed, configuration applied, timer schedule |
| `Debug` / `Trace` | per-item details, diagnostics |

- Guard expensive messages: `if (_log.IsDebugEnabled) { _log.Debug(...); }`. Wrap repeated `Trace` calls in a private `Trace(string message)` helper with the check inside.
- Measure slow operations with a threshold (`ExecutionTimeLoggingThresholdSec`) instead of logging every call.

---

## 6. Concurrency and lifetime

- Lock on a dedicated private object: `private readonly object _lockAnchor = new object();`. Never `lock (this)` or lock on a type or string.
- **Double-checked locking** for one-time initialization:
  ```csharp
  if (_timer.IsRunning()) {
  	return;
  }
  lock (_lock) {
  	if (_timer.IsRunning()) {
  		return;
  	}
  	_timer.Start(...);
  }
  ```
- Copy a shared collection under the lock, then iterate the copy outside it (`GetCurrentLocks()` returns `_lockStore.ToList()`).
- Counters: `Interlocked.Increment(ref _count)`. Shared maps and bags: `ConcurrentDictionary` / `ConcurrentBag`. A field written by one thread and read by others: `volatile`.
- Async library code: `await ... .ConfigureAwait(false)` on every await. Never `.Result` / `.Wait()` in new code.
- `IDisposable`:
  - Release timers, subscriptions and event handlers in `Dispose` (unsubscribe every `+=` you made in a `RemoveEventHandlers()` helper).
  - Track `_isDisposed` and check it in long-running loops and public methods.
  - Full `Dispose(bool disposing)` + finalizer + `GC.SuppressFinalize(this)` only when the class owns unmanaged or background resources.

---

## 7. XML documentation

- Language: English.
- Required on: every public/protected type and member, every interface member, every constructor of public types.
- Implementations of documented interfaces use `/// <inheritdoc />` — don't duplicate the text.
- One-line summary when it fits: `/// <summary>Reports a gauge metric.</summary>`; multi-line otherwise.
- Phrase summaries as third-person verbs: "Creates...", "Returns...", "Provides methods for...", "Initializes new instance of <see cref="X"/>."
- Use `<param>`, `<returns>`, `<value>` for properties, `<see cref="..."/>` for types, `<paramref name="..."/>` for parameters.
- In configuration packages, document private methods too.
- No inline comments that repeat the code. Comment only *why*.

---

## 8. Anti-patterns

| Do not | Do instead |
|---|---|
| `throw new Exception($"Receiver count = 0 ...")`, `throw new Exception("_timer is null")` | Specific exception type (4.2) |
| `DateTime.UtcNow` directly | `IDateTimeProvider` |
| `while (connected) Thread.Sleep(...)` | `await Task.Delay(...)` with cancellation, or events |
| `catch (Exception ex) { Throw...(); }` with `ex` dropped | Pass `ex` as `InnerException` |
| `new Regex(...)` on every call | `private static readonly Regex` |
| JSON built by string concatenation (`$"{{\"SessionId\":\"{id}\"...}}"`) | `JsonConvert.SerializeObject(new { SessionId = id, ... })` |
| Unused locals (`var section = ConfigSection.Value;` never read) | Delete |
| Mutable static fields set from instance code | Instance fields or immutable options object |
| The same property duplicated across sibling classes | One protected helper in the base class |
| Hard-coded values in a factory (`TimeSpan.FromMinutes(1.0)` while the config section is read and ignored) | Use the configuration that was read |

---

## 9. Review checklist

- [ ] Tabs, CRLF, `using` inside the namespace, K&R member braces, braces on every `if`.
- [ ] `#region Class:` wrapper; member regions `Kind: Visibility` in the canonical order; private → public.
- [ ] `_camelCase` private fields, `PascalCase` constants, unit suffixes (`Ms`, `Sec`) on numeric time values.
- [ ] Interface for every service; implementation `internal` unless it is an extension point.
- [ ] Constructor injection only; dependencies `private readonly`; guard clauses with `CheckArgumentNull(nameof(...))`.
- [ ] Convenience constructors only delegate to the full one via `: this(...)`.
- [ ] Registered via `[DefaultBinding]` (configuration) or `AddXxx(this IServiceCollection)` (library).
- [ ] No direct `DateTime.Now/UtcNow`, `Stopwatch`, `Timer` in logic — injected abstractions.
- [ ] No magic strings: keys and literals in `const`; storage keys built by `GetXxxKey()` methods.
- [ ] Cross-cutting logic (retry, timing, throttling) in an executor, not copy-pasted.
- [ ] Specific exception types; `throw;` to rethrow; background callbacks never throw.
- [ ] Named `ILog`; values in `[brackets]`; exception as the second argument; debug/trace guarded.
- [ ] Invalid config → `Warn` + default; fatal config → `ConfigurationErrorsException`.
- [ ] Locks on a private `object`; double-checked init; `ConfigureAwait(false)`; `Dispose` unsubscribes everything.
- [ ] XML docs on the public surface; `<inheritdoc />` on implementations; user-facing text localizable.
