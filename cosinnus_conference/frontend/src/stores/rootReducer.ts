import { combineReducers } from "redux"

import { ThemeReducer, ThemeState } from "./theme/reducer"
import { UserReducer } from "./user/reducer"
import {User} from "./user/models"
import {TranslationsReducer, TranslationsState} from "./translations/reducer"
import {ConferenceReducer} from "./conference/reducer"
import {EventsReducer, EventsState} from "./events/reducer"
import {OrganizationsReducer} from "./organizations/reducer"
import {Organization} from "./organizations/models"
import {RoomReducer} from "./room/reducer"
import {Conference} from "./conference/models"
import {Participant} from "./participants/models"
import {ParticipantsReducer} from "./participants/reducer"
import {Room} from "./room/models"
import {EventParticipantsReducer, EventParticipantsState} from "./eventParticipants/reducer"

export interface RootState {
  events: EventsState,
  eventParticipants: EventParticipantsState,
  organizations: Organization[],
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
  eventParticipants: EventParticipantsReducer,
  organizations: OrganizationsReducer,
  participants: ParticipantsReducer,
  room: RoomReducer,
  theme: ThemeReducer,
  translations: TranslationsReducer,
  user: UserReducer,
})
