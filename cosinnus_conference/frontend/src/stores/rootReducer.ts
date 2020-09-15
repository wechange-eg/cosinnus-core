import { combineReducers } from "redux"

import { ThemeReducer, ThemeState } from "./theme/reducer"
import { UserReducer } from "./user/reducer"
import {User} from "./user/models"
import {TranslationsReducer, TranslationsState} from "./translations/reducer"
import {ConferenceReducer, ConferenceState} from "./conference/reducer"
import {EventSlot, Event} from "./events/models"
import {EventsReducer} from "./events/reducer"
import {DiscussionsReducer} from "./discussions/reducer"
import {WorkshopsReducer} from "./workshops/reducer"
import {CoffeeTablesReducer} from "./coffee_tables/reducer"
import {Channel, ChannelsReducer} from "./channels/reducer"
import {OrganisationsReducer} from "./organisations/reducer"
import {Organisation} from "./organisations/models"

export interface RootState {
  channels: Channel[],
  coffee_tables: Event[],
  conference: ConferenceState,
  discussions: EventSlot[],
  events: EventSlot[],
  organisations: Organisation[],
  theme: ThemeState,
  translations: TranslationsState,
  user: User,
  workshops: EventSlot[],
}

export const rootReducer = combineReducers({
  channels: ChannelsReducer,
  coffee_tables: CoffeeTablesReducer,
  conference: ConferenceReducer,
  discussions: DiscussionsReducer,
  events: EventsReducer,
  organisations: OrganisationsReducer,
  theme: ThemeReducer,
  translations: TranslationsReducer,
  user: UserReducer,
  workshops: WorkshopsReducer,
})
