import {
  ReduxObjectActionCreator, ReduxObjectErrorActionCreator
} from "../../utils/types"
import {ActionType} from "../../constants/actions"
import {Event} from "./models"

export const setFetchEventsLoading: ReduxObjectActionCreator<[string]> = (room) => ({
  type: ActionType.FETCH_EVENTS_LOADING,
  payload: {
    room: room
  }
})

export const setFetchEventsSuccess: ReduxObjectActionCreator<[string, Event[]]> = (room, events) => ({
  type: ActionType.FETCH_EVENTS_SUCCESS,
  payload: {
    room: room,
    events: events
  }
})

export const setFetchEventsError: ReduxObjectErrorActionCreator<[string, string]> = (
  room, errorMessage
) => ({
  type: ActionType.FETCH_EVENTS_ERROR,
  payload: {
    room: room,
    error: Error(errorMessage),
  },
  error: true
})
