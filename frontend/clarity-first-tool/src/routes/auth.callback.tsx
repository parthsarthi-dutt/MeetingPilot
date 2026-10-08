import { createFileRoute, useNavigate, useRouter } from "@tanstack/react-router";
import { useEffect } from "react";
import { z } from "zod";

export const Route = createFileRoute("/auth/callback")({
  validateSearch: z.object({
    token: z.string().catch(""),
  }),
  component: AuthCallback,
});

function AuthCallback() {
  const { token } = Route.useSearch();
  const navigate = useNavigate();
  const router = useRouter();

  useEffect(() => {
    if (token) {
      localStorage.setItem("mp_access_token", token);
      // Force invalidate the router cache so that layout loaders re-run with the new token
      router.invalidate().then(() => {
        navigate({ to: "/onboarding", replace: true });
      });
    } else {
      navigate({ to: "/", replace: true });
    }
  }, [token, navigate, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper text-foreground">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-signal border-t-transparent" />
        <p className="font-mono text-sm uppercase tracking-wider text-muted-ink">
          Authenticating...
        </p>
      </div>
    </div>
  );
}
