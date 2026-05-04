using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Threading.Tasks;

/// <summary>
/// Demonstrates how to buffer and process messages asynchronously using a thread-safe in-memory queue.
/// Use this pattern when an API endpoint or event listener receives data faster than it can be
/// processed — for example, high-frequency webhooks or integration events.
/// ConcurrentQueue&lt;T&gt; is thread-safe and requires no explicit locking.
/// Important: the queue is in-memory only — all data is lost on application restart.
/// Do not use this for guaranteed delivery or persistence; use Creatio queues or a message broker instead.
/// Dequeue and process in a background mechanism (Quartz job, hosted service) — never in the API thread.
/// </summary>
class HowToUseInMemoryQueue {

    // Thread-safe in-memory queue — static so it is shared across all callers in the same AppDomain
    public static readonly ConcurrentQueue<string> Queue = new ConcurrentQueue<string>();

    // Enqueue a message — called from a web service endpoint or event listener
    public static void Enqueue(string body) {
        if (body == null)
            throw new ArgumentNullException("body", "Message body cannot be null.");

        Queue.Enqueue(body);
    }

    // Dequeue all available messages into a batch and process them in parallel
    // Call this from a Quartz job or background service on a fixed interval
    public void ProcessBatch(int maxDegreeOfParallelism) {
        var batch = new List<string>();
        string item;

        // Drain the queue into a local batch — items added after this point go into the next batch
        while (Queue.TryDequeue(out item)) {
            batch.Add(item);
        }

        if (batch.Count == 0) return;

        var options = new ParallelOptions {
            // Tune based on workload: CPU-bound → ProcessorCount, IO-bound → higher
            MaxDegreeOfParallelism = maxDegreeOfParallelism
        };

        Parallel.ForEach(batch, options, body => {
            ProcessSingleMessage(body);
        });
    }

    private void ProcessSingleMessage(string body) {
        // custom processing logic — parse JSON, call ESQ, start a process, etc.
    }
}
