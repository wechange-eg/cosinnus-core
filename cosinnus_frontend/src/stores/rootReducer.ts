import { combineReducers } from "redux"

import { UserReducer } from "./user/reducer"
import {User} from "./user/models"
import {TranslationsReducer, TranslationsState} from "./translations/reducer"
import {Settings} from "./settings/models"
import {SettingsReducer} from "./settings/reducer"
import {SearchReducer, SearchState} from "./search/reducer"
import {AuthState, AuthReducer} from "./auth/reducers";
import { MessageState, MessageReducer } from "./messages/reducers"

export interface RootState {
  auth: AuthState
  settings: Settings
  search: SearchState
  translations: TranslationsState
  user: User,
  message: MessageState
}

export const rootReducer = combineReducers({
  auth: AuthReducer,
  settings: SettingsReducer,
  search: SearchReducer,
  translations: TranslationsReducer,
  user: UserReducer,
  message: MessageReducer
})
