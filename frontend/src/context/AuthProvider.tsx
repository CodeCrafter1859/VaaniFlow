import { useState } from "react";
import type { ReactNode } from "react";
import { request } from "../services/api";
import { AuthContext as Context } from "./AuthContext";
export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState("");
  const [name, setName] = useState("");
  async function login(value: string) {
    const user = await request<{ name: string }>("/auth/me", value);
    setName(user.name);
    setToken(value);
  }
  return (
    <Context.Provider
      value={{
        token,
        name,
        login,
        logout: () => {
          setToken("");
          setName("");
        },
      }}
    >
      {children}
    </Context.Provider>
  );
}
