import React, { useState, useEffect, useRef, useCallback } from "react";
import { flushSync } from "react-dom";
import * as api from "../api";

export function isAnyLLMGenerating(projectId) {
  if (!projectId) return false;
  return (
    localStorage.getItem(`llm_generating_overview_${projectId}`) === "true" ||
    localStorage.getItem(`llm_generating_rec_${projectId}`) === "true" ||
    localStorage.getItem(`llm_generating_topology_${projectId}`) === "true" ||
    localStorage.getItem(`llm_generating_device_${projectId}`) === "true"
  );
}

const LLM_STATUS_POLL_INTERVAL_MS = 3500;

/**
 * One job at a time per project; polls server for shared busy state.
 */
export function useLLMQueue(projectId) {
  const initialBusy = isAnyLLMGenerating(projectId);
  const [llmBusy, setLlmBusy] = useState(initialBusy);
  const [serverLlmBusy, setServerLlmBusy] = useState(false);
  const [serverLlmJobLabel, setServerLlmJobLabel] = useState(null);
  const busyRef = useRef(initialBusy);
  const queueRef = useRef([]);
  busyRef.current = initialBusy;

  useEffect(() => {
    if (!projectId) {
      setServerLlmBusy(false);
      setServerLlmJobLabel(null);
      return;
    }
    let cancelled = false;
    const poll = async () => {
      try {
        const status = await api.getProjectLlmStatus(projectId);
        if (cancelled) return;
        const busy = status && typeof status.busy === "boolean" && status.busy;
        setServerLlmBusy(!!busy);
        setServerLlmJobLabel(busy && status.job_label ? status.job_label : null);
      } catch (_) {
        if (!cancelled) {
          setServerLlmBusy(false);
          setServerLlmJobLabel(null);
        }
      }
    };
    poll();
    const interval = setInterval(poll, LLM_STATUS_POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [projectId]);

  const requestRun = useCallback((runFn) => {
    if (typeof runFn !== "function") return;
    if (!busyRef.current) {
      busyRef.current = true;
      flushSync(() => setLlmBusy(true));
      runFn();
    } else {
      queueRef.current.push(runFn);
      flushSync(() => setLlmBusy(true));
    }
  }, []);

  const onComplete = useCallback(() => {
    if (queueRef.current.length > 0) {
      const next = queueRef.current.shift();
      flushSync(() => setLlmBusy(true));
      next();
    } else {
      busyRef.current = false;
      setLlmBusy(false);
    }
  }, []);

  const effectiveBusy = llmBusy || serverLlmBusy;
  const llmBusyMessage = effectiveBusy
    ? serverLlmBusy && serverLlmJobLabel
      ? `Waiting for LLM: ${serverLlmJobLabel} is running. Please wait.`
      : "An LLM task is running. Please wait."
    : null;
  return { llmBusy: effectiveBusy, requestRun, onComplete, llmBusyMessage };
}
