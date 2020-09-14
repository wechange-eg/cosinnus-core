import {ReduxActionCreator, ReduxErrorActionCreator} from "../../utils/types"
import {ActionType} from "../../constants/actions"
import {EventSlot} from "../events/models"

export const setFetchDiscussionsSuccess: ReduxActionCreator<EventSlot[]> = discussions => ({
  type: ActionType.FETCH_DISCUSSIONS_SUCCESS,
  payload: discussions
})

export const setFetchDiscussionsError: ReduxErrorActionCreator<string> = (
  errorMessage: string
) => ({
  type: ActionType.FETCH_DISCUSSIONS_ERROR,
  payload: Error(errorMessage),
  error: true
})
