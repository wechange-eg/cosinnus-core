import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import axios from "axios";

const API_URL = `${process.env.API_URL}`;

export interface TranslationsResponse {
  locale: string
  catalog: {
    [x: string]: string
  }
}

export interface TranslationsState {
  locale: string
  catalog: {
    [s: string]: string
  }
}

export const fetchTranslations = createAsyncThunk(
  "translations/fetch",
  async (
    values: null,
    { dispatch, getState }
  ): Promise<TranslationsResponse | undefined> => {
    const { data } = await axios.get<TranslationsResponse>(
      `${API_URL}/jsi18n/`,
      values
    );
    return data;
  }
);

const translationSlice = createSlice({
  name: "translations",
  initialState: {} as TranslationsState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchTranslations.fulfilled, (state, action) => {
        if (!action.payload) return;
        state = action.payload;
      })
  },
});

export const { } = translationSlice.actions;
export default translationSlice.reducer;