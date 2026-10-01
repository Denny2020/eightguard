import { User, UserManager, WebStorageStateStore } from "oidc-client-ts";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { AppConfig } from "./config";

/** Sign-in with Keycloak: OIDC authorization code flow with PKCE. Tokens live in sessionStorage
 *  (gone when the tab closes); the strict CSP is the XSS defence that protects them. */
interface Auth {
  user: User | null;
  ready: boolean;
  signIn: (returnTo?: string) => Promise<void>;
  signUp: (returnTo?: string) => Promise<void>;
  signOut: () => Promise<void>;
  accessToken: () => Promise<string>;
}

const AuthContext = createContext<Auth | null>(null);

export function AuthProvider({ config, children }: { config: AppConfig; children: React.ReactNode }) {
  const manager = useMemo(
    () =>
      new UserManager({
        authority: config.authority,
        client_id: config.clientId,
        redirect_uri: `${window.location.origin}/callback`,
        post_logout_redirect_uri: `${window.location.origin}/`,
        response_type: "code",
        scope: "openid profile email",
        userStore: new WebStorageStateStore({ store: window.sessionStorage }),
        automaticSilentRenew: true,
      }),
    [config],
  );
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const done = (u: User | null) => {
      setUser(u && !u.expired ? u : null);
      setReady(true);
    };
    if (window.location.pathname === "/callback") {
      manager
        .signinRedirectCallback()
        .then((u) => {
          const returnTo = typeof u.state === "string" && u.state.startsWith("/") ? u.state : "/";
          window.history.replaceState(null, "", returnTo);
          window.dispatchEvent(new PopStateEvent("popstate"));
          done(u);
        })
        .catch(() => manager.getUser().then(done));
    } else {
      manager.getUser().then(done);
    }
    const loaded = (u: User) => setUser(u);
    const unloaded = () => setUser(null);
    manager.events.addUserLoaded(loaded);
    manager.events.addUserUnloaded(unloaded);
    manager.events.addSilentRenewError(unloaded);
    return () => {
      manager.events.removeUserLoaded(loaded);
      manager.events.removeUserUnloaded(unloaded);
      manager.events.removeSilentRenewError(unloaded);
    };
  }, [manager]);

  const value: Auth = {
    user,
    ready,
    signIn: (returnTo = window.location.pathname) => manager.signinRedirect({ state: returnTo }),
    signUp: (returnTo = window.location.pathname) =>
      manager.signinRedirect({ state: returnTo, extraQueryParams: { prompt: "create" } }),
    signOut: () => manager.signoutRedirect({ id_token_hint: user?.id_token }),
    accessToken: async () => {
      let u = await manager.getUser();
      if (!u || u.expires_in === undefined || u.expires_in < 30) u = await manager.signinSilent();
      if (!u) throw new Error("Not signed in");
      return u.access_token;
    },
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): Auth {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
