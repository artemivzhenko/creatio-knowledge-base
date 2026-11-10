using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json;
using Terrasoft.Core;

/// <summary>
/// Demonstrates how to write, start and read tests that run inside Creatio - the integration tier of the author/tester loop.
/// Some projects keep their tests in a package on the environment instead of a dotnet test project: a base class
/// (UsrBaseTest here), a category per feature, and a runner - a business process or a web service - that runs a
/// category against the real database and answers JSON. Those tests prove what the instance-free unit tier cannot
/// (ESQ against real data, event listeners, SQL functions), and they WRITE to the database: run them only on the
/// project's environment, and let every test clean up the records it creates (a UsrTest_ name prefix makes leftovers findable).
/// Start: `python tools/env/unit.py run --project project.json --category UsrOrders --evidence <file>`; project.json
/// tests.runner names the process (here UsrRunTests_Process, parameter Category, result parameter Result).
/// The answer is JSON inside a string: RunProcess returns it in resultParameterValues.Result; the older
/// ProcessEngineService.svc/UsrRunTests_Process/Execute?ResultParameterName=Result URL wraps it in an XML string
/// element - unit.py unwraps both. Keep the shape {"Tests": [{"Name", "Success", "Message"}]},
/// one item per test; a test that throws is a failure with the exception's message, never a crashed run.
/// The test package depends on the package under test and is pushed and compiled with it (project.json package.consumers).
/// </summary>
class HowToRunTestsInsideCreatio {
}

// 1. The category marker and the base class every test derives from.
[AttributeUsage(AttributeTargets.Class)]
public sealed class UsrTestCategoryAttribute : Attribute {
    public UsrTestCategoryAttribute(string name) {
        Name = name;
    }

    public string Name { get; }
}

public abstract class UsrBaseTest {
    protected UserConnection UserConnection { get; private set; }

    internal void Init(UserConnection userConnection) {
        UserConnection = userConnection;
    }

    // Runs after every test, also when it failed: delete what the test created.
    public virtual void Cleanup() {
    }

    protected static void AreEqual(object expected, object actual, string what) {
        if (!Equals(expected, actual)) {
            throw new UsrAssertException($"{what}: expected {expected ?? "null"}, got {actual ?? "null"}");
        }
    }

    protected static void IsTrue(bool condition, string what) {
        if (!condition) {
            throw new UsrAssertException(what);
        }
    }
}

public class UsrAssertException : Exception {
    public UsrAssertException(string message) : base(message) {
    }
}

// 2. A test: public parameterless void methods of a class in a category.
[UsrTestCategory("UsrOrders")]
public class UsrOrderTotalTest : UsrBaseTest {
    private Guid _orderId;

    public void TotalIsAmountMinusDiscount() {
        var schema = UserConnection.EntitySchemaManager.GetInstanceByName("UsrOrder");
        var order = schema.CreateEntity(UserConnection);
        order.SetDefColumnValues();
        order.SetColumnValue("UsrName", "UsrTest_Order");
        order.SetColumnValue("UsrAmount", 100m);
        order.SetColumnValue("UsrDiscount", 15m);
        order.Save();
        _orderId = order.PrimaryColumnValue;

        order.FetchFromDB(_orderId);
        AreEqual(85m, order.GetTypedColumnValue<decimal>("UsrTotal"), "UsrTotal");
    }

    public override void Cleanup() {
        if (_orderId == Guid.Empty) {
            return;
        }
        var order = UserConnection.EntitySchemaManager.GetInstanceByName("UsrOrder").CreateEntity(UserConnection);
        if (order.FetchFromDB(_orderId)) {
            order.Delete();
        }
    }
}

// 3. The runner: every test of a category (or of one class), one result each, as the JSON unit.py reads.
public class UsrTestRunner {
    private readonly UserConnection _userConnection;

    public UsrTestRunner(UserConnection userConnection) {
        _userConnection = userConnection;
    }

    public string Run(string category, string className = null) {
        var results = new List<object>();
        var testTypes = typeof(UsrTestRunner).Assembly.GetTypes()
            .Where(t => typeof(UsrBaseTest).IsAssignableFrom(t) && !t.IsAbstract)
            .Where(t => !string.IsNullOrEmpty(className)
                ? t.Name == className
                : t.GetCustomAttribute<UsrTestCategoryAttribute>()?.Name == category);
        foreach (var type in testTypes) {
            var tests = type.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly)
                .Where(m => m.ReturnType == typeof(void) && m.GetParameters().Length == 0 && m.Name != nameof(UsrBaseTest.Cleanup));
            foreach (var method in tests) {
                var test = (UsrBaseTest)Activator.CreateInstance(type);
                test.Init(_userConnection);
                try {
                    method.Invoke(test, null);
                    results.Add(new { Name = $"{type.Name}.{method.Name}", Success = true, Message = "" });
                } catch (TargetInvocationException e) {
                    results.Add(new { Name = $"{type.Name}.{method.Name}", Success = false, Message = e.InnerException?.Message ?? e.Message });
                } finally {
                    test.Cleanup();
                }
            }
        }
        return JsonConvert.SerializeObject(new { Tests = results });
    }
}

// 4. The process UsrRunTests_Process: parameters Category (text, in), Class (text, in), Result (unlimited text, out);
//    one script task with this body (a script task is a method body returning bool):
//
//        var runner = new UsrTestRunner(UserConnection);
//        Set("Result", runner.Run(Get<string>("Category"), Get<string>("Class")));
//        return true;
//
//    A process with a script task must be published (compiled) after the push before it starts.
