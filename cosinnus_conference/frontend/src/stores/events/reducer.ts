import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"
import {EventSlot} from "./models"

export interface EventsState {
  [room: string]: EventSlot[]
}

export function EventsReducer(
  state: EventsState = {},
  action: AnyAction
): EventsState {
  switch (action.type) {
    case ActionType.FETCH_EVENTS_SUCCESS: {
      return {
        ...state,
        [action.payload.room]: action.payload.events,
      }
    }
    case ActionType.FETCH_EVENTS_ERROR: {
      return {
        ...state,
        [action.payload.room]: action.payload.events,
      }
    }
    default: {
      return state
    }
  }
}
