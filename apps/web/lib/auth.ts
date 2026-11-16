
import { apiRequest } from "./api";

export type AuthUser = {
  id: number;
  email: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export async function loginUser(
  email: string,
  password: string
): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function registerUser(
  email: string,
  password: string
): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function getCurrentUser(
  token: string
): Promise<AuthUser> {
  return apiRequest<AuthUser>(
    "/auth/me",
    { method: "GET" },
    token
  );
}
