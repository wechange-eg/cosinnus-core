import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"

export interface EventParticipants {
  [event: string]: number
}

export interface EventParticipantsRoomState {
  participants: EventParticipants
  loading: boolean
  error?: Error
}

export interface EventParticipantsState {
  [room: string]: EventParticipantsRoomState
}

export function EventParticipantsReducer(
  state: EventParticipantsState = {},
  action: AnyAction
): EventParticipantsState {
  switch (action.type) {
    case ActionType.FETCH_EVENT_PARTICIPANTS_LOADING: {
      return {
        ...state,
        [action.payload.room]: {
          participants: null,
          loading: true
        }
      }
    }
    case ActionType.FETCH_EVENT_PARTICIPANTS_SUCCESS: {
      return {
        ...state,
        [action.payload.room]: {
          participants: action.payload.participants,
          loading: false
        }
      }
    }
    case ActionType.FETCH_EVENT_PARTICIPANTS_ERROR: {
      return {
        ...state,
        [action.payload.room]: {
          participants: null,
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
