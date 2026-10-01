/** Runtime config, served as /config.json so one image runs in every environment
 *  (Kubernetes mounts a per-environment ConfigMap over it). */
export interface AppConfig {
  authority: string;
  clientId: string;
}

export async function loadConfig(): Promise<AppConfig> {
  const res = await fetch("/config.json", { cache: "no-store" });
  if (!res.ok) throw new Error("Couldn't load /config.json");
  return res.json();
}
