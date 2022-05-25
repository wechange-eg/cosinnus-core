import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {RootState} from "../rootReducer"
import {setUser} from "./actions"
import {User} from "./models"

import UserService from "../../services/user.service"

export const fetchUser: ReduxThunkActionCreator<[], Promise<void>> = () => (
  dispatch: Dispatch,
  _getState: () => RootState
) => {
  return UserService.getUserBoard().then(
    response => {
      dispatch(setUser(User.fromJson(response.data)))
    }
  )
}
