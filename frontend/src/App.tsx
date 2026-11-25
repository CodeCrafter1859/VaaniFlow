import { BrowserRouter } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { AuthProvider } from "./context/AuthProvider";
import { ToastProvider } from "./context/ToastProvider";
import { AppRoutes } from "./routes/AppRoutes";
import { Login } from "./pages/Login";
function Application() {
  const { token } = useAuth();
  return token ? (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  ) : (
    <Login />
  );
}
export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <Application />
      </AuthProvider>
    </ToastProvider>
  );
}
