import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"
import {Event} from "./models"

export interface EventRoomState {
  events: Event[]
  loading: boolean
  error?: Error
}

export interface EventsState {
  [room: string]: EventRoomState
}

export function EventsReducer(
  state: EventsState = {},
  action: AnyAction
): EventsState {
  switch (action.type) {
    case ActionType.FETCH_EVENTS_LOADING: {
      return {
        ...state,
        [action.payload.room]: {
          events: null,
          loading: true
        }
      }
    }
    case ActionType.FETCH_EVENTS_SUCCESS: {
      return {
        ...state,
        [action.payload.room]: {
          events: action.payload.events,
          loading: false
        }
      }
    }
    case ActionType.FETCH_EVENTS_ERROR: {
      return {
        ...state,
        [action.payload.room]: {
          events: null,
          loading: false,
          error: action.payload.error
        }
      }
    }
    default: {
      return state
    }
  }
}
