import { createContext, useContext } from "react";
interface Auth {
  token: string;
  name: string;
  login: (token: string) => Promise<void>;
  logout: () => void;
}
export const AuthContext = createContext<Auth | null>(null);
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("Auth provider missing");
  return value;
}
