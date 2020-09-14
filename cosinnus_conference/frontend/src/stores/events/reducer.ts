import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"
import {EventSlot} from "./models"

export function EventsReducer(
  state: EventSlot[] = null,
  action: AnyAction
): EventSlot[] {
  switch (action.type) {
    case ActionType.FETCH_EVENTS_SUCCESS: {
      return action.payload
    }
    case ActionType.FETCH_EVENTS_ERROR: {
      return state
    }
    default: {
      return state
    }
  }
}
