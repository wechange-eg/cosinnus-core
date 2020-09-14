import {ReduxActionCreator, ReduxErrorActionCreator} from "../../utils/types"
import {ActionType} from "../../constants/actions"
import {EventSlot} from "./models"

export const setFetchEventsSuccess: ReduxActionCreator<EventSlot[]> = events => ({
  type: ActionType.FETCH_EVENTS_SUCCESS,
  payload: events
})

export const setFetchEventsError: ReduxErrorActionCreator<string> = (
  errorMessage: string
) => ({
  type: ActionType.FETCH_EVENTS_ERROR,
  payload: Error(errorMessage),
  error: true
})
