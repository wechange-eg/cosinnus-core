import {configureStore } from "@reduxjs/toolkit";
import { useDispatch } from "react-redux";

import AuthReducer from "./auth";
import SettingsReducer from "./settings";
import TranslationsReducer from "./translations";
import UserReducer from "./user";


export const store = configureStore({
  reducer: {
    auth: AuthReducer,
    settings: SettingsReducer,
    translations: TranslationsReducer,
    user: UserReducer
  }
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
export const useAppDispatch = () => useDispatch<AppDispatch>();
