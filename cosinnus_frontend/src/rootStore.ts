import {configureStore } from "@reduxjs/toolkit";
import { useDispatch } from "react-redux";

import AuthReducer from "./reducers/auth";
import SettingsReducer from "./reducers/settings";
import TranslationsReducer from "./reducers/translations";
import UserReducer from "./reducers/user";


export const store = configureStore({
  reducer: {
    auth: AuthReducer,
    Settings: SettingsReducer,
    translations: TranslationsReducer,
    user: UserReducer
  }
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
export const useAppDispatch = () => useDispatch<AppDispatch>();
