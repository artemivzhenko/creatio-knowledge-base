using System;
using System.Collections.Generic;
using Terrasoft.Core;
using Terrasoft.Core.Process;

/// <summary>
/// Demonstrates how to run a business process synchronously and retrieve an output parameter value.
/// Use this when your code must wait for the process to complete before continuing —
/// for example, when the process computes a result that the calling logic depends on.
/// Execute&lt;TResult&gt; blocks the current thread until the process finishes and returns
/// the value of the specified output parameter cast to TResult.
/// The process schema must be identified by its UId, not its name.
/// For fire-and-forget (asynchronous) execution see HowToRunBusinessProcess.
/// </summary>
class HowToRunBusinessProcessSynchronously {

    public string RunAndGetResult(UserConnection userConnection, Guid contactId) {
        IProcessExecutor processExecutor = userConnection.ProcessEngine.ProcessExecutor;

        // Resolve the schema UId by name — required for the synchronous overload
        Guid schemaUId = userConnection.ProcessSchemaManager
            .GetInstanceByName("MyProcessSchemaName").UId;

        // Input parameters — keys are parameter code names, values are string representations
        var inputParameters = new Dictionary<string, string> {
            { "ContactId", contactId.ToString() }
        };

        // Execute<TResult> runs the process synchronously and returns the value of the named
        // output parameter; the process must complete before this call returns
        string result = processExecutor.Execute<string>(
            schemaUId,
            "OutputParameterName",   // code name of the output parameter to read
            inputParameters);

        return result;
    }

    // Overload: synchronously run a process and get a Guid output parameter
    public Guid RunAndGetGuidResult(UserConnection userConnection) {
        IProcessExecutor processExecutor = userConnection.ProcessEngine.ProcessExecutor;

        Guid schemaUId = userConnection.ProcessSchemaManager
            .GetInstanceByName("MyProcessSchemaName").UId;

        var inputParameters = new Dictionary<string, string>();

        return processExecutor.Execute<Guid>(schemaUId, "CreatedRecordId", inputParameters);
    }
}
