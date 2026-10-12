import { api } from "@/lib/api";
import type { TokenResponse, User } from "@/lib/types";

export interface SignupInput {
  email: string;
  password: string;
  full_name: string;
}

export interface LoginInput {
  email: string;
  password: string;
}

/**
 * Both endpoints take JSON and return the token *plus* the user, so a successful
 * signup logs straight in without a second request.
 */
export async function signup(input: SignupInput): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/signup", input);
  return data;
}

export async function login(input: LoginInput): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/login", input);
  return data;
}

export async function fetchCurrentUser(): Promise<User> {
  const { data } = await api.get<User>("/auth/me");
  return data;
}
