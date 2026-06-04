module interop_test_mod
  use, intrinsic :: iso_fortran_env, only : dp => real64
  implicit none
contains
  function add_numbers(a, b) result(res)
    real(dp), intent(in) :: a, b
    real(dp) :: res
    res = a + b
  end function add_numbers

  subroutine double_array(x)
    real(dp), intent(inout) :: x(:)
    integer :: i
    do i = 1, size(x)
      x(i) = x(i) * 2.0_dp
    end do
  end subroutine double_array

  subroutine scale_matrix(matrix, scale)
    real(dp), intent(inout) :: matrix(:,:)
    real(dp), intent(in) :: scale
    integer :: i, j
    do j = 1, size(matrix, 2)
      do i = 1, size(matrix, 1)
        matrix(i, j) = matrix(i, j) * scale
      end do
    end do
  end subroutine scale_matrix
end module interop_test_mod
