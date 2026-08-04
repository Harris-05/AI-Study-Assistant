import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;

// Supabase's current key model (mid-2025+): a single "publishable" key
// (sb_publishable_...) replaces the old "anon" key -- same low-privilege
// role, same RLS behavior, just an opaque string instead of a JWT. It's
// meant to be public and ships in the client bundle just like anon did.
// If your project hasn't migrated off legacy keys yet, the anon key
// (Settings -> API Keys -> Legacy API Keys tab) still works fine here too.
const supabasePublishableKey =
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabasePublishableKey) {
  // Fails loudly at build/dev time rather than silently breaking every
  // signed-in request later -- these are required, not optional, once auth
  // is wired in.
  console.error(
    "Missing VITE_SUPABASE_URL / VITE_SUPABASE_PUBLISHABLE_KEY -- copy frontend/.env.example to .env and fill them in from Supabase Project Settings -> API Keys."
  );
}

export const supabase = createClient(supabaseUrl, supabasePublishableKey);