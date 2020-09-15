import {ReduxActionCreator, ReduxErrorActionCreator} from "../../utils/types"
import {ActionType} from "../../constants/actions"
import {Channel} from "./reducer"

export const setFetchChannelsSuccess: ReduxActionCreator<Channel[]> = channels => ({
  type: ActionType.FETCH_CHANNELS_SUCCESS,
  payload: channels
})

export const setFetchChannelsError: ReduxErrorActionCreator<string> = (
  errorMessage: string
) => ({
  type: ActionType.FETCH_CHANNELS_ERROR,
  payload: Error(errorMessage),
  error: true
})
