import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, type User } from "../api/client";

export type PersonaRole =
  | "DATA_STEWARD"
  | "BUSINESS_OWNER"
  | "APP_OWNER"
  | "DATA_CONSUMER"
  | "PLATFORM_ADMIN";

export interface IPersonaContextType {
  currentRole: PersonaRole;
  setCurrentRole: (role: PersonaRole) => void;
  currentUser: User | null;
  isDark: boolean;
  setIsDark: React.Dispatch<React.SetStateAction<boolean>>;
  toggleTheme: () => void;
  isCommandPaletteOpen: boolean;
  setIsCommandPaletteOpen: (open: boolean) => void;
  isCreateModalOpen: boolean;
  setIsCreateModalOpen: (open: boolean) => void;
}

const PersonaContext = createContext<IPersonaContextType | undefined>(undefined);

const ROLE_EMAIL_MAP: Record<PersonaRole, string> = {
  DATA_STEWARD: "steward@governance.com",
  BUSINESS_OWNER: "business.owner@governance.com",
  APP_OWNER: "app.owner@governance.com",
  DATA_CONSUMER: "consumer@governance.com",
  PLATFORM_ADMIN: "admin@governance.com",
};

export const PersonaProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = useQueryClient();
  const [currentRole, setCurrentRoleState] = useState<PersonaRole>("DATA_STEWARD");
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isDark, setIsDark] = useState<boolean>(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Sync dark class on <html>
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [isDark]);

  const toggleTheme = useCallback(() => {
    setIsDark((prev) => !prev);
  }, []);

  // Handle persona login and cache invalidation
  const setCurrentRole = useCallback(
    async (role: PersonaRole) => {
      setCurrentRoleState(role);
      const email = ROLE_EMAIL_MAP[role] || ROLE_EMAIL_MAP.DATA_STEWARD;
      try {
        const { user } = await api.login(email, "password123");
        setCurrentUser(user || null);
      } catch (err) {
        console.error("Auto login failed for persona:", role, err);
      } finally {
        queryClient.invalidateQueries();
      }
    },
    [queryClient]
  );

  // Initial login on mount
  useEffect(() => {
    const email = ROLE_EMAIL_MAP[currentRole];
    api.login(email, "password123")
      .then(({ user }) => {
        setCurrentUser(user || null);
        queryClient.invalidateQueries();
      })
      .catch((err) => {
        console.error("Initial login error:", err);
      });
  }, [currentRole, queryClient]);

  return (
    <PersonaContext.Provider
      value={{
        currentRole,
        setCurrentRole,
        currentUser,
        isDark,
        setIsDark,
        toggleTheme,
        isCommandPaletteOpen,
        setIsCommandPaletteOpen,
        isCreateModalOpen,
        setIsCreateModalOpen,
      }}
    >
      {children}
    </PersonaContext.Provider>
  );
};

export function usePersona() {
  const context = useContext(PersonaContext);
  if (!context) {
    throw new Error("usePersona must be used within a PersonaProvider");
  }
  return context;
}
