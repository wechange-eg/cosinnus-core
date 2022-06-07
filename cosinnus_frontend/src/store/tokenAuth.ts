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

export const fetchTokens = createAsyncThunk(
  "auth/fetchToken",
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
    clearTokens(state) {
      state.accessToken = null
      state.refreshToken = null
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchTokens.fulfilled, (state, action) => {
        if (!action.payload) return;
        state.accessToken = action.payload.access;
        state.refreshToken = action.payload.refresh;
      })
      .addCase(fetchTokens.rejected, (state, action) => {
        state.errorMessage = action.error.message;
      })
  },
});

export const { clearTokens } = authSlice.actions;
export default authSlice.reducer;


