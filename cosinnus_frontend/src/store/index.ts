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

import TokenAuthReducer from "./tokenAuth";
import SessionAuthReducer from "./sessionAuth"
import SettingsReducer from "./settings";
import TranslationsReducer from "./translations";
import MessageReducer from "./messages"

const reducers = combineReducers({
  tokenAuth: TokenAuthReducer,
  sessionAuth: SessionAuthReducer,
  settings: SettingsReducer,
  translations: TranslationsReducer,
  message: MessageReducer
 });

 const persistConfig = {
  key: 'root',
  storage,
  whitelist: ['tokenAuth', 'settings'],
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
