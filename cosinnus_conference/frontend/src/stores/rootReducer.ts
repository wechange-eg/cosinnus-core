import { combineReducers } from "redux"

import { ThemeReducer, ThemeState } from "./theme/reducer"
import { UserReducer } from "./user/reducer"
import {User} from "./user/models"
import {TranslationsReducer, TranslationsState} from "./translations/reducer"
import {ConferenceReducer, ConferenceState} from "./conference/reducer"
import {EventsReducer, EventsState} from "./events/reducer"
import {OrganisationsReducer} from "./organisations/reducer"
import {Organisation} from "./organisations/models"

export interface RootState {
  events: EventsState,
  organisations: Organisation[],
  conference: ConferenceState,
  theme: ThemeState,
  translations: TranslationsState,
  user: User,
}

export const rootReducer = combineReducers({
  conference: ConferenceReducer,
  events: EventsReducer,
  organisations: OrganisationsReducer,
  theme: ThemeReducer,
  translations: TranslationsReducer,
  user: UserReducer,
})
