import { combineReducers } from "redux"

import { ThemeReducer, ThemeState } from "./theme/reducer"
import { UserReducer } from "./user/reducer"
import {User} from "./user/models"
import {TranslationsReducer, TranslationsState} from "./translations/reducer"
import {ConferenceReducer, Room} from "./conference/reducer"
import {EventsReducer, EventsState} from "./events/reducer"
import {OrganisationsReducer} from "./organisations/reducer"
import {Organisation} from "./organisations/models"
import {RoomReducer} from "./room/reducer"
import {Conference} from "./conference/models"
import {Participant} from "./participants/models"
import {ParticipantsReducer} from "./participants/reducer"

export interface RootState {
  events: EventsState,
  organisations: Organisation[],
  conference: Conference,
  participants: Participant[],
  room: Room,
  theme: ThemeState,
  translations: TranslationsState,
  user: User,
}

export const rootReducer = combineReducers({
  conference: ConferenceReducer,
  events: EventsReducer,
  organisations: OrganisationsReducer,
  participants: ParticipantsReducer,
  room: RoomReducer,
  theme: ThemeReducer,
  translations: TranslationsReducer,
  user: UserReducer,
})
