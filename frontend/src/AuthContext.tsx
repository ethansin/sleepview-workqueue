import React, { createContext, useContext, useEffect, useState } from "react";
import { getMe, Me } from "./api";

interface AuthContextValue {
  user: Me | null;
  loading: boolean;
  refetch: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  refetch: () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  const fetch = () => {
    setLoading(true);
    getMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetch();
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, refetch: fetch }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
