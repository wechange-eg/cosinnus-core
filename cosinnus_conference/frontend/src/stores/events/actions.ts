import {
  ReduxActionCreator,
  ReduxErrorActionCreator,
  ReduxObjectActionCreator, ReduxObjectErrorActionCreator, ReduxRoomErrorActionCreator,
  ReduxRoomObjectActionCreator
} from "../../utils/types"
import {ActionType} from "../../constants/actions"
import {EventSlot} from "./models"

export const setFetchEventsSuccess: ReduxObjectActionCreator<[string, EventSlot[]]> = (room, events) => ({
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
