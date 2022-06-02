import {configureStore } from "@reduxjs/toolkit";
import storage from 'redux-persist/lib/storage';
import { useDispatch } from "react-redux";
import {combineReducers} from "redux";

import {
  persistReducer,
  FLUSH,
  REHYDRATE,
  PAUSE,
  PERSIST,
  PURGE,
  REGISTER,
} from 'redux-persist'

import AuthReducer from "./auth";
import SettingsReducer from "./settings";
import TranslationsReducer from "./translations";
import UserReducer from "./user";

const reducers = combineReducers({
  auth: AuthReducer,
  settings: SettingsReducer,
  translations: TranslationsReducer,
  user: UserReducer
 });

 const persistConfig = {
  key: 'root',
  storage,
  whitelist: ['auth', 'settings'],
};

const persistedReducer = persistReducer(persistConfig, reducers);


export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
export const useAppDispatch = () => useDispatch<AppDispatch>();
