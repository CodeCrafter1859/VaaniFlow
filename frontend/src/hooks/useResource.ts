import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { request } from "../services/api";
export function useResource<T>(path: string, revision = 0) {
  const { token } = useAuth();
  const key = `${path}:${revision}:${token}`;
  const [result, setResult] = useState<{
    key: string;
    data: T | null;
    error: string;
  }>({ key: "", data: null, error: "" });
  useEffect(() => {
    const controller = new AbortController();
    request<T>(path, token, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setResult({ key, data, error: "" });
      })
      .catch((error: Error) => {
        if (!controller.signal.aborted)
          setResult({ key, data: null, error: error.message });
      });
    return () => controller.abort();
  }, [path, token, key]);
  return {
    data: result.key === key ? result.data : null,
    error: result.key === key ? result.error : "",
    loading: result.key !== key,
  };
}
