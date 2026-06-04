C Legacy Fortran Test Program
program legacy_test
  real*8 :: x
  integer*4 :: i
  double precision :: y
  dimension x(10)
  pointer (ptr_x, x_val)
  parameter (pi = 3.14159d0)
  data y /5.0d0/
  
  structure /vax_struct/
    union
      map
        integer :: val1
      end map
      map
        real :: val2
      end map
    end union
  end structure
  
  x(1) = 3.14
  call process(x(1), y)
  
  do i = 1, 5
    print *, "Iteration", i
  end do

  goto 20
  print *, "This is skipped"
20 print *, "Done"

contains

  subroutine process(in_val, out_val)
    real*8 :: in_val
    double precision :: out_val
    out_val = in_val * 2.0
  end subroutine process

end program legacy_test
