import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import axios from "axios";

export interface AuthState {
  accessToken?: string;
  refreshToken?: string;
  errorMessage?: string;
  isSubmitting?: boolean;
}

export interface AuthResponseData {
  access: string;
  refresh: string;
}

interface LoginFormValues {
  username: string;
  password: string;
}

const API_URL = `${process.env.API_URL}/`;

export const login = createAsyncThunk(
  "auth/login",
  async (
    values: LoginFormValues | null,
  ): Promise<AuthResponseData | undefined> => {
    const { data } = await axios.post<AuthResponseData>(
      `${API_URL}token/`,
      values
    );
    return data;
  }
);

const authSlice = createSlice({
  name: "auth",
  initialState: {} as AuthState,
  reducers: {
    logout(state) {
      state.accessToken = null
      state.refreshToken = null
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.fulfilled, (state, action) => {
          if (!action.payload) return;
          state.accessToken = action.payload.access;
          state.refreshToken = action.payload.refresh;
      })
      .addCase(login.rejected, (state, action) => {
        state.errorMessage = action.error.message;
      })
  },
});

export const { logout } = authSlice.actions;
export default authSlice.reducer;


