import { createContext, useContext, useEffect, useState, useCallback } from "react";
import {
  clearStoredTokenPair,
  getMeApi,
  getStoredTokenPair,
  loginApi,
  registerApi,
  setUnauthorizedHandler,
} from "../utils/api";

const AuthContext = createContext(null);

const getStoredUser = () => {
  try {
    const raw = localStorage.getItem("smartsweep-user");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getStoredUser);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    clearStoredTokenPair();
    setUser(null);
    localStorage.removeItem("smartsweep-user");
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  // Validate stored JWT token on mount
  useEffect(() => {
    async function restoreSession() {
      const { access } = getStoredTokenPair();
      if (access) {
        const result = await getMeApi();
        if (result.success && result.data) {
          const u = result.data;
          const userObj = {
            id: u.id,
            email: u.email,
            username: u.email.split("@")[0],
            name: u.full_name,
            role: u.role,
            ward_id: u.ward_id,
          };
          setUser(userObj);
          localStorage.setItem("smartsweep-user", JSON.stringify(userObj));
        } else {
          logout();
        }
      } else {
        setUser(null);
        localStorage.removeItem("smartsweep-user");
      }
      setLoading(false);
    }
    restoreSession();
  }, [logout]);

  useEffect(() => {
    if (user) {
      localStorage.setItem("smartsweep-user", JSON.stringify(user));
    } else {
      localStorage.removeItem("smartsweep-user");
    }
  }, [user]);

  const login = async (email, password) => {
    const loginRes = await loginApi(email, password);

    if (!loginRes.success) {
      return { success: false, error: loginRes.error };
    }

    const meRes = await getMeApi();
    if (!meRes.success || !meRes.data) {
      return { success: false, error: "Failed to fetch user profile." };
    }

    const profile = meRes.data;
    const userObj = {
      id: profile.id,
      email: profile.email,
      username: profile.email.split("@")[0],
      name: profile.full_name,
      role: profile.role,
      ward_id: profile.ward_id,
    };

    setUser(userObj);
    return { success: true, role: profile.role, name: profile.full_name };
  };

  const register = async (userData) => {
    // 1. Create the account
    const regResult = await registerApi(userData);
    if (!regResult.success) {
      return { success: false, error: regResult.error };
    }

    // 2. Immediately log in to get tokens
    const loginRes = await loginApi(userData.email, userData.password);
    if (!loginRes.success) {
      return { success: false, error: loginRes.error };
    }

    // 3. Fetch the canonical profile (source of truth for role)
    const meRes = await getMeApi();
    if (!meRes.success || !meRes.data) {
      return { success: false, error: "Account created but failed to load profile." };
    }

    const profile = meRes.data;
    const userObj = {
      id: profile.id,
      email: profile.email,
      username: profile.email.split("@")[0],
      name: profile.full_name,
      role: profile.role,
      ward_id: profile.ward_id,
    };

    setUser(userObj);
    return { success: true, role: profile.role, name: profile.full_name };
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
